from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Request
from typing import List, Dict, Any
import os
from werkzeug.utils import secure_filename
from collections import defaultdict
from music21 import *
import math
import base64
from services.database import MongoDatabase
from services.soundslice import SoundsliceService
from api.models import (
    MeasureRequest, MeasureResponse, GenerateRequest,
    SliceRequest, MusicXMLRequest, ExerciseResponse,
    FileDataRequest, FileDataResponse, ExerciseRequest
)
from fastapi.responses import FileResponse
from music.processor import get_music21_score_notation, get_musicxml_from_music21, get_music21_from_music_matrix_representation
from music.exercise import get_all_exercises

# Create router
router = APIRouter()

# Initialize services
db = MongoDatabase()
soundslice = SoundsliceService()

# Configuration
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_DIR)))
MUSIC_DIR = os.path.join(PROJECT_ROOT, "cs99/coda_backend/music_scores")
os.makedirs(MUSIC_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'xml', 'musicxml', 'mxl'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Score hash storage
scoreToScorehash = defaultdict(str)

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working."""
    return {"message": "Router is working!"}

@router.post("/upload_score")
async def upload_score(file: UploadFile = File(...)) -> Response:
    """Upload a MusicXML score file."""
    try:
        if not file:
            raise HTTPException(status_code=400, detail='No file uploaded')
        
        if file.filename == '':
            raise HTTPException(status_code=400, detail='No selected file')

        if not allowed_file(file.filename):
            raise HTTPException(status_code=400, detail='Invalid file type')

        filename = secure_filename(file.filename)
        try:
            # Read file as bytes
            contents = await file.read()    
            try:
                # Validate the file with music21
                _ = converter.parse(contents)
                
                # Save to database
                success = db.save_score(filename, title=filename, composer=None, data=contents)
                if not success:
                    raise HTTPException(status_code=500, detail="Failed to save score to database")
                
                return Response(status_code=200)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f'Invalid MusicXML file: {str(e)}')

        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Invalid MusicXML file: {str(e)}')

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f'Server error: {str(e)}')

@router.get("/list_files", response_model=List[str])
async def list_files() -> List[str]:
    """List all available music files."""
    try:
        scores = db.get_all_scores()
        return [score['score_name'] for score in scores]
    except Exception as e:
        print(f"Error in list_files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@router.post("/get_file_mxl")
async def get_file_mxl(data: FileDataRequest):
    """Get the MXL file data."""
    score = db.get_score(data.filename)
    if score and score.get('data'):
        try:
            file_data = score['data']
            
            # Ensure we're working with bytes
            if not isinstance(file_data, bytes):
                file_data = bytes(file_data)
            
            if data.filename.endswith(".mxl"):
                return Response(
                    content=file_data,
                    media_type="application/vnd.recordare.musicxml+xml",
                    headers={"Content-Disposition": f"attachment; filename={data.filename}"}
                )
            elif data.filename.endswith(".musicxml") or data.filename.endswith(".xml"):
                return Response(
                    content=file_data,
                    media_type="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={data.filename}"}
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid file type")
        except Exception as e:
            print(f"Error processing file data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail="Score not found or no data available")

@router.post("/get_measure_from_second", response_model=MeasureResponse)
async def get_measure_from_second(data: MeasureRequest):
    """Convert a time in seconds to a measure number."""
    score_name = MUSIC_DIR + "/" + data.filename
    score = get_music21_score_notation(score_name)
    
    # Get time signature
    time_signature = score.recurse().getElementsByClass(meter.TimeSignature)[0]
    
    # Get tempo marking
    tempo_marks = score.recurse().getElementsByClass(tempo.MetronomeMark)
    tempo_marking = tempo_marks[0] if tempo_marks else None
    bpm = tempo_marking.number if tempo_marking else 120

    # Calculate measure number
    beats_per_measure = time_signature.numerator
    if bpm is None:
        bpm = 120  # Default to 120 BPM if no tempo marking found
    measure_number = math.floor(data.second / 60 * bpm / beats_per_measure) + 1
    
    return {"measure_number": measure_number}

@router.post("/slice_callback")
async def slice_callback(request: Request):
    """Handle Soundslice callback after notation processing."""
    data = await request.json()
    scorehash = data.get("scorehash")
    success = data.get("success")
    error = data.get("error")
    
    if success == "2":  # Error case
        raise HTTPException(status_code=400)
    
    return Response(status_code=200)

@router.post("/get_slicehash")
async def get_slicehash(data: SliceRequest):
    """Get or create a Soundslice hash for a score."""
    score_name = data.filename
    if score_name in scoreToScorehash:
        return {"slicehash": scoreToScorehash[score_name]}
    else:
        scorehash = soundslice.create_and_upload_slice(score_name, data.musicxml, data.title, data.composer)

        # if the score is an exercise, look in a different part of the mongoDB server
        if data.is_exercise:
            score = db.get_exercise(score_name)
            if score:
                db.update_exercise_with_slicehash(score_name, scorehash)
            else:
                db.save_exercise(score_name, score_hash=bytes(scorehash, 'utf-8'), title=data.title, composer=data.composer, data=None)
        else:
            if db.get_score(score_name):
                db.update_score_with_slicehash(score_name, scorehash)
            else:
                db.save_score(score_name, score_hash=bytes(scorehash, 'utf-8'), title=data.title, composer=data.composer, data=None)

        scoreToScorehash[score_name] = scorehash
        return {"slicehash": scorehash}

@router.post("/save_musicxml_to_file")
async def save_musicxml_to_file(data: MusicXMLRequest):
    """Save MusicXML content to a file."""
    try:
        with open(data.filename, 'w') as f:
            f.write(data.musicxml)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/generate", response_model=ExerciseResponse)
async def generate_exercises(data: GenerateRequest):
    """Generate exercises from a score excerpt."""
    score_excerpt = get_music21_score_notation(
        MUSIC_DIR + "/" + data.filename,
        data.start_measure,
        data.end_measure
    )
    
    # Get all exercises
    raw_exercises = get_all_exercises(score_excerpt)
    
    # Filter out None values and invalid tuples
    filtered_exercises = {}
    for category, exercises in raw_exercises.items():
        valid_exercises = [
            (desc, xml) for desc, xml in exercises 
            if desc is not None and xml is not None
        ]
        if valid_exercises:  # Only include categories with valid exercises
            filtered_exercises[category] = valid_exercises
    
    return {
        "exercises": filtered_exercises,
        "start_measure": data.start_measure,
        "end_measure": data.end_measure
    } 