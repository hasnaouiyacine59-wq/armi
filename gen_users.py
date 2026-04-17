import random
from faker import Faker

fake = Faker()

def generate_user():
    fname = fake.first_name()
    lname = fake.last_name()
    num = random.randint(100, 9999)

    return {
        "first_name": fname,
        "last_name": lname,
        "email": f"{fname.lower()}.{lname.lower()}@techxbox.eu.org",
        "username": f"{fname.lower()}{lname.lower()}{num}",
        "password": f"{fname}{lname}{num}!",
    }

if __name__ == "__main__":
    for user in [generate_user() for _ in range(5)]:
        for k, v in user.items():
            print(f"{k}: {v}")
        print()
