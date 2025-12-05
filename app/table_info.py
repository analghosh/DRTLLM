TABLE_INFO = """
Table: updated_case_details_2025
Columns:
- diary_no (string) - Unique diary number assigned to the case
- filing_no (string) - Filing number of the case
- case_no (string) - Court case number
- case_type (string) - Type/category of the case Foregin key relationship for 'case_type' table 1 and 6 for original application, 4 and 7 for securitization application
- case_filing_date (string) - Date when the case was filed
- case_registration_date (string) - Date when the case was registered
- petitioner_name (string) - Name of the petitioner
- respondent_name (string) - Name of the respondent
- case_status (string) - Current status of the case 'D' for 'disposed' and 'P' for 'pending'
- scrutiny_notification_date (string) - Date when scrutiny notification was issued
- scrutiny_compliance_date (string) - Date when scrutiny compliance happened
- scrutiny_objection_status_1_2 (string) - Scrutiny objection status (e.g., level 1/2)
- case_first_listing_date (string) - Date of first listing/hearing of the case
- suit_amount (string) - Claimed suit amount for the case
- daily_order_uploaded_date (string) - Date when daily order was uploaded
- final_order_upload (string) - Path/URL of final order document
- document_upload_url (string) - Path/URL of the uploaded supporting document
- master_doc_name (string) - Master document type or filename
- doc_name (string) - Specific document name or description
- case_disposed_off_date (string) - Date when the case was disposed
- scrutiney_time (string) - Time taken for scrutiny (e.g., days)
- case_listing_time (string) - Time taken to list the case (e.g., days)
- disposal_diffdays (string) - Days between filing and disposal
- drt_name (string) - Tribunal/DRT name
- filing_no_rank_no (string) - Ranking of filing number

Table: case_type 
- case_type_name columns contains different cases of applications like Original Applications, standard etc.
Columns: 
- case_type_id (string) - case type master 
- case_type_name (string) - case type name different cases

"""
