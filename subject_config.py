# add more hsc subjects as needed

subject_data = {
    "MSTD": {"name": "Mathematics Standard", "colour": "blue"},
    "MADV": {"name": "Mathematics Advanced", "colour": "blue"},
    "MEX1": {"name": "Mathematics Extension 1", "colour": "blue"},
    "MEX2": {"name": "Mathematics Extension 2", "colour": "blue"},
    "ESTD": {"name": "English Standard", "colour": "purple"},
    "EADV": {"name": "English Advanced", "colour": "purple"},
    "EEX1": {"name": "English Extension 1", "colour": "purple"},
    "EEX2": {"name": "English Extension 2", "colour": "purple"},
    "PHY": {"name": "Physics", "colour": "green"},
    "CHE": {"name": "Chemistry", "colour": "indigo"},
    "BIO": {"name": "Biology", "colour": "pink"},
    "EES": {"name": "Earth and Environmental Science", "colour": "teal"},
    "ECO": {"name": "Economics", "colour": "yellow"},
    "BUS": {"name": "Business Studies", "colour": "orange"},
    "LEG": {"name": "Legal Studies", "colour": "red"},
    "MOD": {"name": "Modern History", "colour": "yellow"},
    "PDH": {"name": "PDHPE", "colour": "lime"},
    "SEN": {"name": "Software Engineering", "colour": "gray"},
    "ENT": {"name": "Enterprise Computing", "colour": "cyan"},
}

# Reverse map: Full subject name -> Code
name_to_code = {info["name"]: code for code, info in subject_data.items()}
