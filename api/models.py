from pydantic import BaseModel
from typing import Optional, Dict, List, Any

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

class ExerciseResponse(BaseModel):
    exercises: Dict[str, List[tuple[Optional[str], Optional[str]]]]
    start_measure: int
    end_measure: int 

class FileDataRequest(BaseModel):
    filename: str

class FileDataResponse(BaseModel):
    data: str