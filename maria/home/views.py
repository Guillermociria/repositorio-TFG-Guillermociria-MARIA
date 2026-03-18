from django.shortcuts import render
from .forms import DynamicFeatureForm
import json
from pathlib import Path

def index(request):
    response = None
    '''
    if request.method == "POST":
        prompt = request.POST.get("prompt")
        response = ask_llm(prompt)
    '''
    return render(request, "home.html", {
        "response": response
    })



BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "llm" / "feature_models/feature_model1.json") as f:
    feature_json = json.load(f)
    
def feature_form_view(request):
    response = None
    if request.method == "POST":
        # Aquí se puede procesar los datos seleccionados
        response = request.POST
    return render(request, "feature_form.html", {
        "feature_root": feature_json["featureModel"]["root"],
        "response": response
    })