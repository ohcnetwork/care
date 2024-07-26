from django import template

register = template.Library()


@register.filter(name="format_prescription")
def format_prescription(prescription):
    if prescription.dosage_type == "TITRATED":
        return f"{prescription.medicine_name}, titration from {prescription.base_dosage} to {prescription.target_dosage}, {prescription.route}, {prescription.frequency} for {prescription.days} days."
    if prescription.dosage_type == "PRN":
        return f"{prescription.medicine_name}, {prescription.base_dosage} to {prescription.max_dosage}, Should have minimum {prescription.min_hours_between_doses} hours between two doses, Indicated by {prescription.indicator}"
    else:
        return f"{prescription.medicine_name}, {prescription.base_dosage}, {prescription.route}, {prescription.frequency} for {prescription.days} days."
