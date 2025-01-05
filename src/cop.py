
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class BookmakerStorage():

    def __init__(self) -> None:
        self.bookmakers = []

    def loadBookmakers(self):
        try:
            with open("bookmakers.json", "r") as final:
                self.bookmakers = json.load(final)
        except FileNotFoundError:
            print("File bookmakers.json not found.")
        except:
            print("Errors with json file.")

    async def getBookmakers(self):
        return self.bookmakers

    async def addBookmaker(self, wallet):
        self.bookmakers.append(wallet)

    async def deleteBookmaker(self, id):
        self.bookmakers.pop(id)

    async def editBookmaker(self, id, data):
        self.bookmakers[id] = data

    async def saveBookmakersDB(self):
        with open("bookmakers.json", "w") as final:
            json.dump(self.bookmakers, final)
