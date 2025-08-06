import google.generativeai as genai
import os
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ============= ENUMS FOR CATEGORIES =============
class ObjectCategory(str, Enum):
    # Consumer Electronics
    SMARTPHONE = "Smartphone"
    TABLET = "Tablet"
    LAPTOP = "Laptop"
    DESKTOP_COMPUTER = "Desktop Computer"
    MONITOR = "Monitor"
    TELEVISION = "Television"
    GAMING_CONSOLE = "Gaming Console"
    SMARTWATCH = "Smartwatch"
    EARBUDS = "Earbuds/Headphones"
    CAMERA = "Digital Camera"
    
    # Computer Components
    CIRCUIT_BOARD = "Circuit Board"
    HARD_DRIVE = "Hard Drive"
    RAM = "RAM Module"
    PROCESSOR = "CPU/Processor"
    GRAPHICS_CARD = "Graphics Card"
    POWER_SUPPLY = "Power Supply Unit"
    SSD = "Solid State Drive"
    MOTHERBOARD = "Motherboard"
    
    # Batteries
    LITHIUM_BATTERY = "Lithium-ion Battery"
    ALKALINE_BATTERY = "Alkaline Battery"
    LEAD_ACID_BATTERY = "Lead-acid Battery"
    BUTTON_BATTERY = "Button Cell Battery"
    LAPTOP_BATTERY = "Laptop Battery Pack"
    PHONE_BATTERY = "Phone Battery"
    
    # Cables and Accessories
    CABLES = "Cables/Wires"
    CHARGER = "Charger/Adapter"
    KEYBOARD = "Keyboard"
    MOUSE = "Mouse"
    USB_DEVICE = "USB Device/Flash Drive"
    
    # Large Appliances
    PRINTER = "Printer"
    SCANNER = "Scanner"
    ROUTER = "Router/Modem"
    SPEAKER = "Speaker System"
    MICROWAVE = "Microwave"
    
    # Other
    MIXED_EWASTE = "Mixed E-waste"
    UNKNOWN = "Unknown Device"

class ConditionStatus(str, Enum):
    INTACT = "Intact"
    BROKEN = "Broken"
    PARTIALLY_DAMAGED = "Partially Damaged"
    SEVERELY_DAMAGED = "Severely Damaged"
    BURNED = "Burned/Melted"
    WATER_DAMAGED = "Water Damaged"

class ShredSafety(str, Enum):
    SAFE_TO_SHRED = "Safe to Shred"
    DO_NOT_SHRED = "Do Not Shred"
    REQUIRES_PREPROCESSING = "Requires Preprocessing Before Shredding"

class ProcessingMethod(str, Enum):
    SHRED = "Shred"
    MANUAL_DISASSEMBLY = "Manual Disassembly"
    BATTERY_REMOVAL = "Battery Removal Required"
    DATA_DESTRUCTION = "Data Destruction Required"
    SPECIALIZED_RECYCLING = "Specialized Recycling"
    HAZMAT_HANDLING = "Hazardous Material Handling"

# ============= PYDANTIC MODELS =============
class HazardousComponents(BaseModel):
    has_battery: bool = Field(description="Contains battery that could explode/leak")
    has_mercury: bool = Field(description="Contains mercury (LCD screens, old monitors)")
    has_lead: bool = Field(description="Contains lead (CRT monitors, solder)")
    has_capacitors: bool = Field(description="Contains capacitors that may hold charge")
    has_toner: bool = Field(description="Contains toner/ink (printers)")
    has_data_storage: bool = Field(description="Contains data storage that needs wiping")

class EWasteAnalysis(BaseModel):
    # Basic Classification
    object_type: ObjectCategory
    brand: Optional[str] = Field(default=None, description="Brand if identifiable")
    model: Optional[str] = Field(default=None, description="Model if identifiable")
    
    # Condition Assessment
    condition: ConditionStatus
    
    # Safety Assessment
    shred_safety: ShredSafety
    safety_notes: List[str] = Field(default_factory=list, description="Specific safety concerns")
    
    # Processing Instructions
    primary_processing: ProcessingMethod
    preprocessing_steps: List[str] = Field(default_factory=list, description="Steps before main processing")
    processing_notes: str = Field(description="Detailed processing instructions")
    
    # Component Analysis
    hazardous_components: HazardousComponents
    
    # Compliance and Sorting
    disposal_category: str = Field(description="Category for sorting: Hazardous, Standard, Special Handling")
    
    # Additional Observations
    observations: str = Field(description="Any additional relevant observations")
    confidence_score: float = Field(description="Confidence in identification (0-1)")

# ============= ANALYSIS FUNCTIONS =============
def create_analysis_schema():
    """Create the JSON schema for Gemini API"""
    return {
        "type": "object",
        "properties": {
            "object_type": {
                "type": "string",
                "enum": [e.value for e in ObjectCategory],
                "description": "Type of electronic waste"
            },
            "brand": {
                "type": "string",
                "description": "Brand name if visible",
                "nullable": True
            },
            "model": {
                "type": "string",
                "description": "Model number if visible",
                "nullable": True
            },
            "condition": {
                "type": "string",
                "enum": [e.value for e in ConditionStatus],
                "description": "Physical condition of the item"
            },
            "shred_safety": {
                "type": "string",
                "enum": [e.value for e in ShredSafety],
                "description": "Whether item is safe to shred"
            },
            "safety_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific safety concerns"
            },
            "primary_processing": {
                "type": "string",
                "enum": [e.value for e in ProcessingMethod],
                "description": "Primary processing method"
            },
            "preprocessing_steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Required preprocessing steps"
            },
            "processing_notes": {
                "type": "string",
                "description": "Detailed processing instructions"
            },
            "hazardous_components": {
                "type": "object",
                "properties": {
                    "has_battery": {"type": "boolean"},
                    "has_mercury": {"type": "boolean"},
                    "has_lead": {"type": "boolean"},
                    "has_capacitors": {"type": "boolean"},
                    "has_toner": {"type": "boolean"},
                    "has_data_storage": {"type": "boolean"}
                },
                "required": ["has_battery", "has_mercury", "has_lead", 
                           "has_capacitors", "has_toner", "has_data_storage"]
            },
            "disposal_category": {
                "type": "string",
                "description": "Sorting category for disposal"
            },
            "observations": {
                "type": "string",
                "description": "Additional observations"
            },
            "confidence_score": {
                "type": "number",
                "description": "Confidence score between 0 and 1"
            }
        },
        "required": ["object_type", "condition", "shred_safety", "primary_processing", 
                    "processing_notes", "hazardous_components", "disposal_category", 
                    "observations", "confidence_score"]
    }

def analyze_ewaste(image_file, prompt_file="prompts/prompt_main.md", additional_context=""):
    """
    Analyze e-waste image and return comprehensive processing instructions
    
    Args:
        image_file: Path to the image file
        prompt_file: Path to the prompt file (default: prompts/prompt_main.md)
        additional_context: Any additional context about the item
    
    Returns:
        EWasteAnalysis object with complete analysis
    """
    # Read prompt from file
    try:
        with open(prompt_file, "r") as f:
            prompt = f.read()
        
        # Add additional context if provided
        if additional_context:
            prompt += f"\n\nAdditional context: {additional_context}"
    except FileNotFoundError:
        print(f"Warning: Prompt file '{prompt_file}' not found. Using default prompt.")
        # Fallback to a basic prompt if file not found
        prompt = """You are an expert E-waste Safety Analyzer. Analyze the image and identify:
        1. The type of electronic device
        2. Its condition
        3. Whether it's safe to shred
        4. Any hazardous components
        5. Processing instructions
        
        Focus on safety and provide clear guidance."""

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        image = genai.upload_file(image_file)
        
        response = model.generate_content(
            [prompt, image],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=create_analysis_schema()
            )
        )
        
        # Parse and validate response
        result_dict = json.loads(response.text)
        analysis = EWasteAnalysis(**result_dict)
        
        return analysis
        
    except Exception as e:
        print(f"Error analyzing image: {e}")
        raise

def generate_processing_report(analysis: EWasteAnalysis) -> str:
    """Generate a human-readable processing report"""
    report = f"""
╔════════════════════════════════════════════════════════════╗
║          E-WASTE SAFETY & PROCESSING REPORT               ║
║                {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                     ║
╚════════════════════════════════════════════════════════════╝

📦 ITEM IDENTIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type: {analysis.object_type}
Brand: {analysis.brand or 'Not identified'}
Model: {analysis.model or 'Not identified'}
Condition: {analysis.condition}
Confidence: {analysis.confidence_score:.1%}

⚠️  SAFETY ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shred Safety: {analysis.shred_safety}
Disposal Category: {analysis.disposal_category}
"""
    
    if analysis.safety_notes:
        report += "\nSafety Concerns:\n"
        for note in analysis.safety_notes:
            report += f"  ⚡ {note}\n"
    
    report += f"""
☣️  HAZARDOUS COMPONENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Battery: {'⚠️ YES' if analysis.hazardous_components.has_battery else '✓ No'}
Mercury: {'⚠️ YES' if analysis.hazardous_components.has_mercury else '✓ No'}
Lead: {'⚠️ YES' if analysis.hazardous_components.has_lead else '✓ No'}
Capacitors: {'⚠️ YES' if analysis.hazardous_components.has_capacitors else '✓ No'}
Toner/Ink: {'⚠️ YES' if analysis.hazardous_components.has_toner else '✓ No'}
Data Storage: {'⚠️ YES' if analysis.hazardous_components.has_data_storage else '✓ No'}

🔧 PROCESSING INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary Method: {analysis.primary_processing}

Processing Notes:
{analysis.processing_notes}
"""
    
    if analysis.preprocessing_steps:
        report += "\nPreprocessing Required:\n"
        for i, step in enumerate(analysis.preprocessing_steps, 1):
            report += f"  {i}. {step}\n"
    
    report += f"""
📝 ADDITIONAL OBSERVATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{analysis.observations}

════════════════════════════════════════════════════════════
"""
    
    return report

# ============= MAIN EXECUTION =============
if __name__ == "__main__":
    # Example usage
    image_path = "images/iphone.jpeg"
    
    try:
        print("🔍 Analyzing e-waste image...")
        analysis = analyze_ewaste(image_path)
        
        # Generate and print report
        report = generate_processing_report(analysis)
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"ewaste_report_{timestamp}.txt"
        with open(report_filename, "w") as f:
            f.write(report)
        print(f"📄 Report saved to {report_filename}")
        
        # Save JSON for database/API
        json_filename = f"ewaste_analysis_{timestamp}.json"
        with open(json_filename, "w") as f:
            json.dump(analysis.dict(), f, indent=2)
        print(f"💾 JSON data saved to {json_filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")