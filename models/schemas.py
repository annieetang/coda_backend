from pydantic import BaseModel
from typing import Optional

class MeasureRequest(BaseModel):
    filename: str
    second: float

class MeasureResponse(BaseModel):
    measure_number: int

class GenerateRequest(BaseModel):
    filename: str
    start_measure: int
    end_measure: int

class SliceRequest(BaseModel):
    filename: str
    musicxml: Optional[str] = None
    title: Optional[str] = None
    composer: Optional[str] = None

class MusicXMLRequest(BaseModel):
    filename: str
    musicxml: str 

class ExerciseRequest(BaseModel):
    filename: str
    musicxml: str
    title: Optional[str] = None
    composer: Optional[str] = None

class ExerciseResponse(BaseModel):
    slicehash: str