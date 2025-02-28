"""Windows and Mac run configuration values"""

WINDOWS_PROJECT_DIR = (
    "Y:\\garf\\Kris\\Projects\\NjCpaExpressWrongRenSolAppFix_20241211\\"
)


def windows():
    """
    Provides configuration settings for Windows environment.

    This function returns a dictionary containing various file paths and settings
    specific to the Windows operating system for the application.

    Returns:
        dict: A dictionary with the following keys:
            - send_list_path (str): Path to the CPA Express list file.
            - smtp_host (str): SMTP server host address.
            - applications_path (str): Path to the CPA applications directory.
            - signature_html_path (str): Path to the HTML signature file.
            - insured_plain_text_email_template_path (str): Path to the plain text email 
                template for insured.
            - co_producer_email_template_path (str): Path to the HTML email template 
                for co-producer.
            - insured_email_template_path (str): Path to the HTML email template for insured.
            - postgres_host (str): PostgreSQL database host address.
    """
    return {
        "send_list_path": WINDOWS_PROJECT_DIR + "CPA_Express_1022.txt",
        "smtp_host": "10.0.0.33",
        "applications_path": "Y:\\mailmerge\\CPA\\",
        "signature_html_path": WINDOWS_PROJECT_DIR + "signature.html",
        "insured_plain_text_email_template_path": WINDOWS_PROJECT_DIR
            + "insured_plain_text_email_template.txt",
        "co_producer_email_template_path": WINDOWS_PROJECT_DIR
            + "CoProducerEmailTemplate.html",
        "insured_email_template_path": WINDOWS_PROJECT_DIR
            + "InsuredEmailTemplate.html",
        "postgres_host": "localhost",
    }


MAC_PROJECT_DIR = (
    "/Volumes/pdf_files/garf/Kris/Projects/NjCpaExpressWrongRenSolAppFix_20241211/"
)


def mac():
    """
    Provides configuration settings for Mac environment.

    This function returns a dictionary containing various file paths and settings
    specific to the Mac operating system for the application.

    Returns:
        dict: A dictionary with the following keys:
            - send_list_path (str): Path to the CPA Express list file.
            - smtp_host (str): SMTP server host address.
            - applications_path (str): Path to the CPA applications directory.
            - signature_html_path (str): Path to the HTML signature file.
            - insured_plain_text_email_template_path (str): Path to the plain text email 
                template for insured.
            - co_producer_email_template_path (str): Path to the HTML email template for 
                co-producer.
            - insured_email_template_path (str): Path to the HTML email template for insured.
            - postgres_host (str): PostgreSQL database host address.
    """
    return {
        "send_list_path": MAC_PROJECT_DIR + "CPA_Express_1022.txt",
        "smtp_host": "10.0.0.33",
        "applications_path": "/Volumes/pdf_files/CPA/",
        "signature_html_path": MAC_PROJECT_DIR + "signature.html",
        "insured_plain_text_email_template_path": MAC_PROJECT_DIR
            + "insured_plain_text_email_template.txt",
        "co_producer_plain_text_email_template_path": MAC_PROJECT_DIR
            + "co_producer_plain_text_email_template.txt",
        "co_producer_email_template_path": MAC_PROJECT_DIR
            + "CoProducerEmailTemplate.html",
        "insured_email_template_path": MAC_PROJECT_DIR + "InsuredEmailTemplate.html",
        "postgres_host": "10.0.0.51",
    }
