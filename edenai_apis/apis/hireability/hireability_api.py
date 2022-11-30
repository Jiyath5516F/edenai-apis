from io import BufferedReader
import requests
import sys
from pprint import pprint
from edenai_apis.features import Ocr
from edenai_apis.features.ocr import (
    ResumeEducationEntry,
    ResumeExtractedData,
    ResumeLang,
    ResumeParserDataClass,
    ResumePersonalInfo,
    ResumePersonalName,
    ResumeSkill,
    ResumeLocation,
    ResumeWorkExp,
    ResumeWorkExpEntry,
)

from edenai_apis.loaders.data_loader import ProviderDataEnum
from edenai_apis.loaders.loaders import load_provider
from edenai_apis.features.base_provider.provider_api import ProviderApi
from edenai_apis.utils.exception import ProviderException
from edenai_apis.utils.types import ResponseType


class HireabilityApi(ProviderApi, Ocr):
    provider_name = "hireability"

    def __init__(self):
        super().__init__()
        self.api_settings = load_provider(ProviderDataEnum.KEY, self.provider_name)
        self.product_code = self.api_settings["product_code"]
        self.url = self.api_settings["endpoint"]

    def ocr__resume_parser(
        self, file: BufferedReader
    ) -> ResponseType[ResumeParserDataClass]:

        files = {'document': file}

        # Generate Api output
        try:
            response = requests.post(self.url, data={
            'product_code' : self.product_code,
            'document_title' : file.name,
            }, files=files)
            original_response = response.json()
        except Exception as exc:
            raise ProviderException(f"Unexpected error! {sys.exc_info()[0]}") from exc
        # Handle provider error
        #errors = original_response['Results'][0]['HireAbilityJSONResults'][1]['ProcessingErrors'][0]
        #print("The errors are ", errors)
        # if errors['Error'][0]['ErrorMessage']:
        #     raise ProviderException(errors['Error'][0]['ErrorMEssage'],code = errors['Error'][0]['ErrorCode'])  
        
        infos = original_response['Results'][0]['HireAbilityJSONResults'][0]      

        # Resume parser std 
        
        # 1. Personal informations
        # 1.1 Resume name
        personal_names = ResumePersonalName(
            raw_name = infos.get('FormattedName',''), first_name = infos.get('GivenName',''), 
            last_name = infos.get('FamilyName','')
        )
        # 1.2 Address
        address = ResumeLocation(
            country_code = infos.get('CountryCode',''), region = infos.get('CountrySubDivisionCode',''),
            postal_code = infos.get('PostalCode',''), street = infos.get('AddressLine',''),
            city = infos.get('CityName','')
        )
        # 1.3 Others
        personal_infos = ResumePersonalInfo(
            name = personal_names,
            address=address,
            phones=[phone['Number'] for phone in infos.get('Phone') if phone['Number']],
            mails=[mail['Address'] for mail in infos.get('Email') if mail['Address']],
            urls=[],
            gender = infos.get('Gender',''),
            date_of_birth = infos.get('DateOfBirth',''),
            place_of_birth = infos.get('PlaceOfBirth',''),
            nationality = infos.get('Nationality',''),
            marital_status = infos.get('MaritalStatus',''),
            objective = infos.get('Objective',''),
            current_salary = infos.get('Salary','')
        )

        # 2 Education
        edu_entries = []
        for i in infos.get("EducationOrganizationAttendance",{}):
            title = i.get('EducationLevel',[{}])[0].get('Name','')
            location = ResumeLocation(
                country_code = i.get('ReferenceLocation',{}).get('CountryCode',''),
                region = i.get('ReferenceLocation',{}).get('CountrySubDivisionCode',''),
                city = i.get('ReferenceLocation',{}).get('CityName','')
            )
            edu_entries.append(
                ResumeEducationEntry(
                    start_date=i.get("AttendanceStartDate"),
                    end_date=i.get("AttendanceEndDate"),
                    establishment=i.get("School"),
                    location = location,
                    title=title,
                    description = i.get('MajorProgramName',[''])[0],
                    gpa = i.get('EducationScore',[''])[0],
                )
            )
        edu = ResumeEducationEntry(entries=edu_entries)

        # 3 Work experience
        work_entries = []
        for i in infos.get("PositionHistory",{}):
            work_location = ResumeLocation(
                country_code = i.get('ReferenceLocation',{}).get('CountryCode',''),
                region = i.get('ReferenceLocation',{}).get('CountrySubDivisionCode',''),
                city = i.get('ReferenceLocation',{}).get('CityName','')
            )
            work_entries.append(
                ResumeWorkExpEntry(
                    title=i.get("PositionTitle",''),
                    company=i.get("Employer",''),
                    start_date=i.get("StartDate",''),
                    end_date=i.get("EndDate",''),
                    description=i.get("Description",''),
                    location=work_location,
                    industry = i.get('Industry',{}).get('Name')
                )
            )
        duration = infos.get("TotalYearsOfExperience")
        work = ResumeWorkExp(total_years_experience=duration, entries=work_entries)

        # 4 Others
        skills = []
        for i in infos.get("PersonCompetency",''):
            skill = i.get("CompetencyName",'')
            skill_type = i.get("CompetencyLevel",'')
            skills.append(ResumeSkill(name=skill, type=skill_type))

        languages = [ResumeLang(name=i.get('LanguageCode')) for i in infos.get("Languages", [])]
        certifications = [ResumeSkill(name=i.get('CertificationName')) for i in infos.get("Certification", [])]

        std = ResumeParserDataClass(
            extracted_data=ResumeExtractedData(
                personal_infos=personal_infos,
                education=edu,
                work_experience=work,
                languages=languages,
                skills=skills,
                certifications=certifications,
            )
        )

        result = ResponseType[ResumeParserDataClass](
            original_response=original_response, standarized_response=std
        )
        return result
