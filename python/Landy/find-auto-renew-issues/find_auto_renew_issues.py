"""Read auto_rate.sh and find accounts with claims"""

import re
from configparser import ConfigParser
import psycopg2
from datetime import datetime, timedelta


def load_config(filename="/Users/kristoferpearson/Dev/scripts/python/Landy/find-auto-renew-issues/database.ini", section="postgresql"):
    """
    Load configuration settings from a file.

    This function reads a configuration file and returns a dictionary containing the settings for a specified section.
    If the section is not found, an exception is raised.

    Parameters:
    filename (str): The name of the configuration file. Default is 'database.ini'.
    section (str): The name of the section to retrieve settings from. Default is 'postgresql'.

    Returns:
    dict: A dictionary containing the configuration settings for the specified section.

    Raises:
    Exception: If the specified section is not found in the configuration file.
    """
    parser = ConfigParser()
    parser.read(filename)

    # get section, default to postgresql
    ret_config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            ret_config[param[0]] = param[1]
    else:
        raise KeyError(f"Section {section} not found in the {filename} file")

    return ret_config


def find_auto_renew_issues(db_config):
    """Read auto_renew.sh and find accounts with claims"""
    auto_renewed_accounts = []
    with open(
        "/Volumes/pdf_files/garf/Kris/Projects/AutoRenewIssue_20240926/auto_rate.sh",
        "r",
        encoding="utf8",
    ) as auto_renew_file, psycopg2.connect(**db_config) as conn:
        cur = conn.cursor()
        for line in auto_renew_file:
            risk_num = re.search(r"\w{4}\d{2}-\d", line)
            if risk_num is not None and risk_num.group() not in auto_renewed_accounts:
                auto_renewed_accounts.append(risk_num.group())
                cur.execute("""SELECT cg.firm_name, cg.total_incurred
                                FROM claims_gaclaims cg 
                                JOIN cpa_icustomer ci ON cg.policy_num = SUBSTRING(ci.policy_num, 4, 7) 
                                WHERE ci.risk_num = %s
                                LIMIT 5;
                            """,
                            (risk_num.group(), ))
                account_data = cur.fetchone()
                if account_data is not None and datetime.strptime(account_data[0], '%m/%d/%Y') > (datetime.today() - timedelta(days = 1826)) and account_data[1] > 0:
                    print(f"Risk Number: {risk_num.group()}")
                    print(account_data)

if __name__ == "__main__":
    config = load_config()
    print(config)
    find_auto_renew_issues(config)
