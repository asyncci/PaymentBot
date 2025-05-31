import hashlib, asyncio
from logging import error, log
from os import getenv
from dotenv import load_dotenv
import httpx
from datetime import datetime, timezone

class CashdeskAPI:
    BASE_URL = "https://partners.servcul.com/CashdeskBotAPI"

    def __init__(self, hash_key: str, cashier_pass: str, login: str, cashdesk_id: int):
        self.hash = hash_key
        self.cashierpass = cashier_pass
        self.login = login
        self.cashdesk_id = cashdesk_id

    def _md5(self, s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()

    def _sha256(self, s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()

    def _headers(self, part1: str, part2: str) -> dict:
        combined = self._sha256(part1 + part2)
        return {"sign": combined}

    def _confirm(self, *args) -> str:
        return self._md5(":".join(map(str, args)))

    async def get_balance(self):
        dt = datetime.now(timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
        confirm = self._confirm(self.cashdesk_id, self.hash)

        part1 = f"hash={self.hash}&cashierpass={self.cashierpass}&dt={dt}"
        part2 = f"dt={dt}&cashierpass={self.cashierpass}&cashdeskid={self.cashdesk_id}"
        headers = self._headers(self._sha256(part1), self._md5(part2))

        url = f"{self.BASE_URL}/Cashdesk/{self.cashdesk_id}/Balance"
        params = {"confirm": confirm, "dt": dt}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
            return resp.json()

    async def get_user(self, user_id: int):
        confirm = self._confirm(user_id, self.hash)

        part1 = f"hash={self.hash}&userid={user_id}&cashdeskid={self.cashdesk_id}"
        part2 = f"userid={user_id}&cashierpass={self.cashierpass}&hash={self.hash}"
        headers = self._headers(self._sha256(part1), self._md5(part2))

        url = f"{self.BASE_URL}/Users/{user_id}"
        params = {"confirm": confirm, "cashdeskId": self.cashdesk_id}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params)
            return resp.json()

    async def deposit(self, user_id: int, amount: float, lng: str = "ru"):
        confirm = self._confirm(user_id, self.hash)

        part1 = f"hash={self.hash}&lng={lng}&userid={user_id}"
        part2 = f"summa={amount}&cashierpass={self.cashierpass}&cashdeskid={self.cashdesk_id}"
        headers = self._headers(self._sha256(part1), self._md5(part2))

        url = f"{self.BASE_URL}/Deposit/{user_id}/Add"
        json_data = {
            "cashdeskId": self.cashdesk_id,
            "lng": lng,
            "summa": amount,
            "confirm": confirm
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=json_data)
            return resp.json()

    async def payout(self, user_id: int, code: str, lng: str = "ru"):
        confirm = self._confirm(user_id, self.hash)

        part1 = f"hash={self.hash}&lng={lng}&userid={user_id}"
        part2 = f"code={code}&cashierpass={self.cashierpass}&cashdeskid={self.cashdesk_id}"
        headers = self._headers(self._sha256(part1), self._md5(part2))

        url = f"{self.BASE_URL}/Deposit/{user_id}/Payout"
        json_data = {
            "cashdeskId": self.cashdesk_id,
            "lng": lng,
            "code": code,
            "confirm": confirm
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=json_data)
            return resp.json()




load_dotenv()
try:
    HASH_KEY = getenv("HASH_KEY")
    assert HASH_KEY is not None, "HASH_KEY must not be None"
    
    CASHIER_PASS = getenv("CASHIER_PASS")
    assert CASHIER_PASS is not None, "CASHIER_PASS must not be None"

    LOGIN = getenv("LOGIN")
    assert LOGIN is not None, "LOGIN must not be None"
    
    cashdeskId = getenv("CASHDESK_ID")
    assert cashdeskId is not None, "CASHDESK_ID must not be None"
    CASHDESK_ID = int(cashdeskId)

except:
    error('One of those: HASH_KEY, CASHIER_PASS, LOGIN, CASHDESK_ID; was not provided.')
    quit()

api = CashdeskAPI(
    hash_key=HASH_KEY,
    cashier_pass=CASHIER_PASS,
    login=LOGIN,
    cashdesk_id=CASHDESK_ID,
)

#balance = asyncio.run(api.get_balance())
#user = asyncio.run(api.get_user(202929329))
#if "errorCode" in user:
#    print(user['invalidFields'])
#else:
#    print(user)

#deposit = asyncio.run(api.deposit(626363517, 1.0))
#print(deposit)


#payout = asyncio.run(api.payout(626363517, code="sldap"))
#print(payout)

#print(balance['Balance'])
#print(user)
#print(deposit)
#print(payout)
