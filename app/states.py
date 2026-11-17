from aiogram.fsm.state import StatesGroup, State

class AddAnimal(StatesGroup):
    code = State(); kind = State(); breed = State(); sex = State(); age = State(); weight = State(); date = State(); price = State(); photo = State(); note = State()
class AddFeed(StatesGroup):
    name = State(); quantity = State(); price = State(); date = State(); supplier = State()
class AddWeight(StatesGroup):
    value = State()
class AddSchedule(StatesGroup):
    times = State(); items = State()
class EditReminder(StatesGroup):
    amounts = State()
class AddNote(StatesGroup):
    body = State()
class AddExpense(StatesGroup):
    category = State(); amount = State(); date = State(); description = State()
class AddIncome(StatesGroup):
    category = State(); amount = State(); date = State(); description = State()
class SearchAnimals(StatesGroup):
    query = State()
class SellAnimal(StatesGroup):
    price = State(); sale_date = State()
class RestoreBackup(StatesGroup):
    file = State()
class SetFeedAlert(StatesGroup):
    value = State()
class EditAnimal(StatesGroup):
    value = State()

class AddAnimalPhoto(StatesGroup):
    photo = State()
