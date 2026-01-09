import re

input_file = "data_no_messages.sql"
output_file = "cleaned_data.sql"

with open(input_file, "r") as f:
    content = f.read()

# 1. Remove MySQL system comments and wrappers
content = re.sub(r"/\*.*?\*/;", "", content)
content = re.sub(r"LOCK TABLES.*?;", "", content)
content = re.sub(r"UNLOCK TABLES;", "", content)

# 2. Convert MySQL backticks (`) to nothing (or double quotes if needed)
content = content.replace("`", "")

# 3. Handle Boolean differences (MySQL 1/0 to Postgres true/false)
# WARNING: Only do this if you know your 1/0 values are strictly for booleans.
# If you have counts (like globes), skip this or target specific tables.
# content = content.replace(",1,", ",true,").replace(",0,", ",false,")

with open(output_file, "w") as f:
    f.write(content)

print(f"Cleaned file created: {output_file}")
