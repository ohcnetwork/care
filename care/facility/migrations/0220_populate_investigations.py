from django.db import migrations

investigations = """name	unit	ideal	min	max	type (Float/String/Choice)	choices	category_id
Blood Group					Choice	A-,A+,B+,B-,O+,O-,AB-,AB+	1
Total Count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
Neutrophil count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
Lymphocyte count Eosinophil count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
Eosinophil count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
Basophil count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
Monocyte count	cell/cumm	4500-11000 cells/cumm	4500	11000	Float		1
neutrophil	%	4500-11000 cells/cumm	4500	11000	Float		1
lymphocyte	%	4500-11000 cells/cumm	4500	11000	Float		1
eosinophil	%	4500-11000 cells/cumm	4500	11000	Float		1
basophile	%	4500-11000 cells/cumm	4500	11000	Float		1
monocyte	%	4500-11000 cells/cumm	4500	11000	Float		1
Hb	gm%	men 14-17 gm% , woman 12-16 gm% ,children 12-14 gm%	12	17	Float		1
PCV	%	Men 38-51 gm% , Woman 36-47%	36	51	Float		1
RBC count	million/cumm	4.5-6.0 million/cumm	4.5	6	Float		1
RDW	%	11.8 - 16.1%	11.8	16.1	Float		1
Platelets	lakhs/cumm	1.5-4.5 lakhs/cumm	1.5	4.5	Float		1
MCV	Fl	80-96 Fl	80	96	Float		1
MCH	pg	27-33 pg	27	33	Float		1
MCHC	g/dl	33.4-35.5 g/dl	33.4	35.5	Float		1
ESR	mm/hr	0-20 mm/hr	0	20	Float		1
Peripheral blood smear					String		1
Reticulocyte count	%	adults 0.5-1.5%, newborns 3-6%	0.5	6	Float		1
M P smear					String		1
FBS	mg/dl	70-110 mg/dl	70	110	Float		2
PPBS	mg/dl	< 140 mg/dl	0	140	Float		2
RBS	mg/dl	80-120 mg/dl	80	120	Float		2
T. Cholestrol	mg/dl	150-220 mg/dl	150	220	Float		2
LDL	mg/dl	< 130 mg/dl	0	130	Float		2
HDL	mg/dl	male 35-80 mg/dl, female 40-88 mg/dl	35	88	Float		2
Triglycerides	mg/dl	male 60-165 mg/dl, female 40-140 mg/dl	40	165	Float		2
VLDL	mg/dl	2-30 mg/dl	2	30	Float		2
Urea	mg/dl	10-50 mg/dl	10	50	Float		2
Uric Acid	mg/dl	male 3.5-7.2 mg/dl, female 2.6-6 mg/dl	2.6	7.2	Float		2
Creatinine	mg/dl	male 0.7-1.4 mg/dl, female 0.6-1.2 mg/dl	0.6	1.4	Float		2
CRP	mg/l	upto 6 mg/l	0	6	Float		2
Serum Sodium (Na+)	mmol/l	135-155 mmol/l	135	155	Float		2
Serum Potassium (K+)	mmol/l	3.5 - 5.5 mmol/l	3.5	5.5	Float		2
Serum Calcium	mg/dl	8.8-10.2 mg/dl	8.8	10.2	Float		2
Serum Phosphorus	mg/dl	children 4-7 mg/dl, adult 2.5-4.5 mg/dl	2.5	7	Float		2
Serum Chloride	mmol/l	96-109 mmol/l	96	109	Float		2
Serum Megnesium	mg/dl	1.6-2.6 mg/dl	1.6	2.6	Float		2
Total Bilirubin	mg/dl	adult upto 1.2 mg/dl, infant 0.2-8 mg/dl	0.2	8	Float		2
Direct Bilirubin	mg/dl	upto 0.4 mg/dl	0	0.4	Float		2
SGOT	IU/L	upto 46 IU/L	0	46	Float		2
SGPT	IU/L	upto 49 IU/L	0	49	Float		2
ALP	IU/L	male 80-306 IU/L, female 64-306 IU/L	64	306	Float		2
Total Protein	g/dl	6-8 g/dl	6	8	Float		2
Albumin	g/dl	3.5-5.2 g/dl	3.5	5.2	Float		2
Globulin	g/dl	1.5-2.5 g/dl	1.5	2.5	Float		2
PT	sec	9.1-12.1 seconds	9.1	12.1	Float		2
INR	sec	0.8-1.1 seconds	0.8	1.1	Float		2
APTT	sec	25.4-38.4 seconds	25.4	38.4	Float		2
D-Dimer	ug/l	< 0.5 ug/l	0	0.5	Float		2
Fibrinogen	mg/dl	200-400 mg/dl	200	400	Float		2
GCT	mg/dl	< 140 mg/dl	0	140	Float		2
GTT	mg/dl	140-200 mg/dl	140	200	Float		2
GGT	U/L	11-50 U/L	11	50	Float		2
HbA1C	%	4-5.6 %	4	5.6	Float		2
Serum Copper	mcg/dl	85-180 mcg/dl	85	180	Float		2
Serum Lead	mcg/dl	upto 10 mcg/dl	0	10	Float		2
Iron	mcg/dl	60-170 mcg/dl	60	170	Float		2
TIBC	mcg/dl	250-450 mcg/dl	250	450	Float		2
Transferin Saturation	%	15-50 %	15	50	Float		2
IL6	pg/ml	0-16.4 pg/ml	0	16.4	Float		2
Lactate	mmol/l	0.5-1 mmol/l	0.5	1	Float		2
Ceruloplasmin	mg/dl	14-40 mg/dl	14	40	Float		2
ACP	U/L	0.13-0.63 U/L	0.13	0.63	Float		2
Protein C	IU dl 1	65-135 IU dl 1	65	135	Float		2
Protein S	%	70-140 %	70	140	Float		2
G6PD	U/g Hb	neonate 10.15-14.71 U/g Hb, adult 6.75-11.95 U/g Hb			Float		2
ACCP	EU/ml	< 20 EU/ml	0	20	Float		2
Ferritin	ng/ml	20-250 ng/ml	20	250	Float		2
LDH	U/L	140-280 U/L	140	280	Float		2
Amylase	U/L	60-180 U/L	60	180	Float		2
Lipase	U/L	0-160 U/L	0	160	Float		2
Ammonia	ug/dL	15-45 ug/dL	15	45	Float		2
CKMB	IU/L	5-25 IU/L	5	25	Float		2
CK NAC	U/L	male < 171 U/L, female < 145 U/L			Float		2
24hrs Urine Protein	mg/dl	<10 mg/dl	0	10	Float		2
24hrs Urine Uric Acid	mg/24hr	250-750 mg/24hr	250	750	Float		2
24 hrs Urine Oxalate	mg/L	<15 mg/L	0	15	Float		2
Urine Microalbumin	mg	< 30 mg	0	30	Float		2
Urine Sodium	mEq/day	40-220 mEq/day	40	220	Float		2
PCT	ng/ml	< 0.15 ng/ml	0	0.15	Float		2
T3	ng/dl	80-220 ng/dl	80	220	Float		2
T4	ug/L	5-12 ug/L	5	12	Float		2
TSH	mIU/L	0.5-5 mIU/L	0.5	5	Float		2
FT3	ng/dl	60-180 ng/dl	60	180	Float		2
FT4	ng/dl	0.7-1.9 ng/dl	0.7	1.9	Float		2
Estradiol	pg/ml	premenopausal women 30-400 pg/ml, post-menopausal women 0-30 pg/ml, men 10-50 pg/ml			Float		2
Growth Hormone	ng/ml	male 0.4-10 ng/ml, female 1-14 ng/ml	0.4	14	Float		2
Cortisol	mcg/dl	5-25 ng/ml	5	25	Float		2
PTH	pg/ml	14-65 pg/ml	14	65	Float		2
Prolactine	ng/ml	male <20 ng/ml, female <25 ng/ml, pregnant women <300 ng/ml			Float		2
Pro BNP	pg/ml	< 300 pg/ml	0	300	Float		2
Vitamine D3	ng/ml	20-40 ng/ml	20	40	Float		2
Vitamine B12	pg/ml	160-950 pg/ml	160	950	Float		2
FSH	IU/L	before puberty 0-4 IU/L, during puberty 0.36-10 IU/L, 	0	10	Float		2
LH	IU/L	before menopause 5-25 IU/L, after menopause 14.2-52.3 IU/L	5	52.3	Float		2
PSA	ng/ml	<4 ng/ml	0	4	Float		2
ACTH	pg/ml	10-60 pg/ml	10	60	Float		2
CEA	ng/ml	0-2.5 ng/ml	0	2.5	Float		2
AFP	ng/ml	10-20 ng/ml	10	20	Float		2
CA125	U/ml	< 46 U/ml	0	46	Float		2
CA19.9	U/ml	0-37 U/ml	0	37	Float		2
Testosterone 	ng/dl	270-1070 ng/dl	270	1070	Float		2
Progestrone	ng/ml	female pre ovulation, menupausal women, men <1 ng/ml, mid-cycle 5-20 ng/ml			Float		2
Serum IgG	g/L	6-16 g/L	6	16	Float		2
Serum IgE	UL/ml	150-1000 UL/ml	150	1000	Float		2
Serum IgM	g/L	0.4-2.5 g/L	0.4	2.5	Float		2
Serum IgA	G/L	0.8-3 g/L	0.8	3	Float		2
Colour					String		3
Appearence					String		3
Ph					String		3
Specific Gravity					String		3
Nitrite					String		3
Urobilinogen					String		3
Bile Salt					String		3
Bile Pigment					String		3
Acetone					String		3
Albumin					String		3
Sugar					String		3
Puscells					String		3
Epithetical Cells					String		3
RBC 					String		3
Cast					String		3
Crystal					String		3
others					String		3
UPT					String		3
Stool OB					String		3
Stool Microscopy					String		3"""


investigation_groups = """Id	Name
1	Haematology 
2	Biochemistry test
3	Urine Test"""


def none_or_float(val):
    if len(val.strip()) != 0:
        return float(val)
    return None


def populate_investigations(apps, *args):
    PatientInvestigation = apps.get_model("facility", "patientinvestigation")
    PatientInvestigationGroup = apps.get_model("facility", "patientinvestigationgroup")
    investigation_group_data = investigation_groups.split("\n")[1:]
    investigation_group_dict = {}
    for investigation_group in investigation_group_data:
        current_investigation_group = investigation_group.split("\t")
        current_obj = PatientInvestigationGroup.objects.filter(name=current_investigation_group[1]).first()
        if not current_obj:
            current_obj = PatientInvestigationGroup(name=current_investigation_group[1])
            current_obj.save()
        investigation_group_dict[current_investigation_group[0]] = current_obj
    investigation_data = investigations.split("\n")[1:]
    for investigation in investigation_data:
        current_investigation = investigation.split("\t")
        data = {
            "name": current_investigation[0],
            "unit": current_investigation[1],
            "ideal_value": current_investigation[2],
            "min_value": none_or_float(current_investigation[3]),
            "max_value": none_or_float(current_investigation[4]),
            "investigation_type": current_investigation[5],
            "choices": current_investigation[6],
        }
        current_obj = PatientInvestigation.objects.filter(**data).first()
        if not current_obj:
            current_obj = PatientInvestigation(**data)
            current_obj.save()
        current_obj.groups.add(investigation_group_dict[current_investigation[7]])
        current_obj.save()


def reverse_populate_investigations(apps, *args):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("facility", "0219_remove_investigationsession_session"),
    ]

    operations = [migrations.RunPython(populate_investigations, reverse_code=reverse_populate_investigations)]
