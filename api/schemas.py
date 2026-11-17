from pydantic import BaseModel, Field, ConfigDict

class AnimalCreate(BaseModel):
    code: str | None = Field(default=None, max_length=40)
    kind: str
    breed: str = ""
    age_months: int = Field(default=0, ge=0, le=1200)
    current_weight: float = Field(default=0, ge=0)
    purchase_date: str = ""
    purchase_price: float = Field(default=0, ge=0)
    note: str = ""

class AnimalUpdate(BaseModel):
    breed: str | None = None
    age_months: int | None = Field(default=None, ge=0, le=1200)
    current_weight: float | None = Field(default=None, ge=0)
    note: str | None = None
    status: str | None = None

class WeightCreate(BaseModel):
    weight: float = Field(gt=0)
    recorded_date: str | None = None
    note: str = ""

class FeedPurchaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    purchased_at: str
    supplier: str = ""

class MoneyCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    date: str
    description: str = ""
    animal_id: int | None = None

class AnimalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    kind: str
    breed: str
    sex: str
    age_months: int
    current_weight: float
    purchase_date: str
    purchase_price: float
    note: str
    status: str
