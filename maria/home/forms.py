from django import forms
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar el JSON
with open(BASE_DIR / "llm" / "feature_models/feature_model1.json") as f:
    feature_json = json.load(f)

def generate_fields(node, prefix=""):
    """
    Genera campos de formulario recursivamente desde un nodo del JSON
    """
    fields = {}
    node_name = prefix + node["name"]
    node_type = node.get("type", "optional")
    
    # Solo nodos que no tienen children
    if "children" not in node or not node["children"]:
        # mandatory → required checkbox
        required = node_type == "mandatory"
        fields[node_name] = forms.BooleanField(
            label=node["name"],
            required=required
        )
        return fields

    # Nodo con children
    for child in node.get("children", []):
        child_fields = generate_fields(child, prefix=node_name + "__")
        fields.update(child_fields)
    
    return fields

# Crear los campos a partir del root
fields_dict = generate_fields(feature_json["featureModel"]["root"])

# Crear clase de formulario dinámicamente
DynamicFeatureForm = type("DynamicFeatureForm", (forms.Form,), fields_dict)