from werkzeug.security import check_password_hash, generate_password_hash

password = generate_password_hash("December@2020")
newPass = generate_password_hash("December@2020")
print(newPass)
print(password)
print(check_password_hash(password, "December@2020"))