from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

class GenerateInput(BaseModel):
    # input values for model generation of bbox
    label: List[int] = Field(..., example=[0,1,2], title='labels to be in the layout')
    num_label: int = Field(..., example=3, title='number of labels available for the layout')

class EditInput(BaseModel):
    # values to edit existing bbox layout based on relational constraints
    id_a: int = Field(..., example=2, title='first box ID')
    id_b: int = Field(..., example=1, title='second box ID')
    relation: str = Field(..., example='equal', title='type of relation between boxes')
    bbox: List[List[float]] = Field(..., example=[[0.5, 0.5, 0.25, 0.25]], title='current layout')
    label: List[int] = Field(..., example=[0,1,2], title='labels to be in the layout')
    num_label: int = Field(..., example=3, title='number of labels available for the layout')

class ModelResult(BaseModel):
    bbox: List[List[float]] = Field(..., example=[[0.5, 0.5, 0.25, 0.25]], title='bbox of layout')
    label: List[int] = Field(..., example=[0,1,2], title='labels of the layout')

class ModelResponse(BaseModel):
    error: bool = Field(..., example=False, title='whether there is error')
    results: ModelResult = ...

class ErrorResponse(BaseModel):
    error: bool = Field(..., example=True, title='whether there is error')
    message: str = Field(..., example='', title='error message')