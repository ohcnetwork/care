#import "@preview/fontawesome:0.2.0": *

#set page("a4")
#set text(font: "IBM Plex Sans")
#set text(hyphenate: false)
#let mygray = luma(150)

// Heading
#align(center, text(28pt)[= Facility Dummy])

#line(length: 100%, stroke: mygray)

// Section 1
#grid(
    columns: (auto, 1fr),
    row-gutter: 1em,
    align: (left, right),

    // Name
    text(size: 18pt)[= Patient Discharge Report],

    // Logo
    grid.cell(align: right, rowspan: 2)[#scale(x:90%, y:90%, reflow: true)[#image("logoCare.svg")]],

    // Created on Date
    [#text(fill: mygray, weight: 200)[*Created on #datetime.today().display("[day]/[month]/[year]")*]]
)


#line(length: 100%, stroke: mygray)


#show grid.cell.where(x: 0): set text(stroke:mygray, weight: 200)
#show grid.cell.where(x: 2): set text(stroke:mygray, weight: 200)

#grid(
  columns: (1fr,1fr,1fr,1fr),
  row-gutter: 1.5em,
  [Full name:],[Dummy Patient 3],
  [Gender:],[Male],
  [Age:],[23],
  [Date of Birth:],[01/01/2000],
  [Blood Group:],[0+],
  [Phone Number:],[+919640229897],
  [Address:],grid.cell(colspan: 3,"Test Patient address address address address address address address address address address address address ") ,
)

#line(length: 100%, stroke: mygray)


#align(left, text(18pt,)[== Admission Details])
#text("")

#grid(
  columns: (1.1fr,2fr),
  row-gutter: 1.2em,
  align: (left),
  [Route to Facility:], [Internal transfer within the facility],
  [Decision after consultation:], [Admission],
  [Date of Admission:], [March 18, 2024, 1:06 p.m.],
  [IP No:], [45],
  [Weight:], [0.0 kg],
  [Height:], [0.0 cm],
  [Symptoms at admission:], [Sore Throat, Cough],
  [From:], [Feb. 29, 2024],
)


#align(center,[#line(length: 40%, stroke: mygray,)])


#align(left, text(16pt,)[=== Health Insurance Details])

#let frame(stroke) = (x, y) => (
  left: if x > 0 { 0pt } else { stroke },
  right: stroke,
  top: if y < 2 { stroke } else { 0pt },
  bottom: stroke,
)

#set table(
  fill: (_, y) => if calc.odd(y) { rgb("EAF2F5") },
  stroke: frame(rgb("21222C")),
)


#table(
  columns: (1.2fr, 2fr, 1fr,1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*INSURER NAME*], [*ISSUER ID*], [*MEMBER ID*],[*POLICY ID*],
  ),
  "Swasth", "saurabhsth-hcx-staging@h ealthcare-app.com", "SUB0545", "POL014&7853434343",
  "HealthCare", "john.doe@healthcarefdfdfdfdffd-app.com", "SUB02434", "POL02",
  "MediCare", "jane.doe@medicare-system.org", "SUB03", "POL03",
  "Wellness", "alex.smith@wellness-hub.net", "SUB04", "POL04",
  "LifeLine", "emma.jones@lifeline-connect.io", "SUB05", "POL05",
  "HealthCare", "john.doe@healthcare-app.com", "SUB02", "POL02",
  "MediCare", "jane.doe@medicare-system.org", "SUB03", "POL03",
  "Wellness", "alex.smith@wellness-hub.net", "SUB04", "POL04",
  "LifeLine", "emma.jones@lifeline-connect.io", "SUB05", "POL05",
)



#align(center,[#line(length: 40%, stroke: mygray,)])


#align(left, text(16pt,)[=== Unconfirmed Diagnoses (as per ICD-11):])

#table(
  columns: (1.5fr, 3.5fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*ID*], [*NAME*],
  ),
  "441539", "6C4A.5 Alcohol addiction",
  "441539", "6C4A.5 Alcohol addiction",
)
#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== Medication History:])

#table(
  columns: (1.5fr, 3.5fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*COMORBIDITY*], [*DETAILS*],
  ),
  "441539", "6C4A.5 Alcohol addiction",
  "441539", "6C4A.5 Alcohol addiction",
)
#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== Health status at admission:])
#text("")
#grid(
  columns: (1fr,2fr),
  gutter: 1.4em,
  align: (left),
  [Present health condition:], [Min Breathlessness with Body Pain],
  [Ongoing Medication:], [Paracetamol],
  [History of present illness:], [sample],
  [Allergies], [sample],
  [Examination details and Clinical conditions:], [ data sample data sample data],
)

#text("")
#align(center,[#line(length: 100%, stroke: mygray,)])

#align(left, text(18pt,)[== Treatment Summary])
#text("")


#align(left, text(16pt,)[=== Prescription Medication:])
#table(
  columns: (1fr, 1fr, 1fr,1fr,1fr,1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*MEDICINE*], [*DOSAGE*], [*ROUTE*],[*FREQUENCY*],[*DAYS*],[*NOTES*]
  ),
  "PIRAZOLE-DSR - omeprazole + doone - dsasd ","12 mg","IV","TID","None","Sample notes very very very  very very very  very very very long",
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","Sample BIG_WORD_ERROR",
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","SAmple notes",
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","sample notes",
)



#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== PRN Prescription:])
#table(
  columns: (1fr, 1fr, 1fr,1fr,1fr,1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*MEDICINE*], [*DOSAGE*], [*MAX DOSAGE*],[*MINIMUM TIME BETWEEN 2 DOSES*],[*ROUTE*],[*INDICATOR*]
  ),
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","very very very very very very very veryyyyyyyyyyyy very very very very very big data",
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","dsds",
  "PIRAZOLE-DSR - omeprazole + doone - ","12 mg","IV","TID","None","dsds",

)
#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== General Instructions (Advice):])
#lorem(200)




#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== Lab Reports:])
#table(
  columns: (1.5fr, 1fr, 1fr,1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*REQUESTED ON*], [*SAMPLE TYPE*], [*LABEL*],[*RESULT*],
  ),
  "March 31, 2024, 11:48 p.m","Blood in EDTA","ICMR","AWAITING",
  "March 31, 2024, 11:48 p.m","Blood in EDTA","ICMR","AWAITING",
  "March 31, 2024, 11:48 p.m","Blood in EDTA","ICMR","AWAITING",
  "March 31, 2024, 11:48 p.m","Blood in EDTA","ICMR","AWAITING",
)


#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== Daily Rounds:])
#text("")

#rect(width: 100%,height: auto,inset: 20pt,radius: 20pt )[
  == March 19, 2024, 3:54 p.m
  #text(fill:mygray,size: 13pt)[=== Category]
  #lorem(20)
  #text(fill:mygray,size: 13pt)[=== Physical Examination Details]
  #lorem(20)
  #text(fill:mygray,size: 13pt)[=== Other Details]
  #lorem(20)
  #text(fill:mygray,size: 13pt)[=== Symptoms]
  #lorem(20)
]




#align(center,[#line(length: 40%, stroke: mygray,)])

#align(left, text(16pt,)[=== Investigation History:])
#table(
  columns: (1fr, 1fr, 1fr,1fr,1fr),
  inset: 10pt,
  align: horizon,
  table.header(
    [*GROUP*], [*NAME*], [*RESULT*],[*RANGE*],[*DATE*],
  ),
  "Haematology","Neutrophil count","Negative","4500.0 - 11000.0 cell/cumm","March 23, 2024, 3:17 p.m",
  "Haematology","Neutrophil count","Negative","4500.0 - 11000.0 cell/cumm","March 23, 2024, 3:17 p.m",
  "Haematology","Neutrophil count","Negative","4500.0 - 11000.0 cell/cumm","March 23, 2024, 3:17 p.m",
  "Haematology","Neutrophil count","Negative","4500.0 - 11000.0 cell/cumm","March 23, 2024, 3:17 p.m",

)


#align(center,[#line(length: 40%, stroke: mygray,)])


#align(left, text(18pt,)[== Discharge Summary])
#grid(
  columns: (1.1fr,2fr),
  row-gutter: 1.2em,
  align: (left),
  [Discharge Date::], [March 23, 2024, 3:17 p.m],
  [Discharge Reason:], [Admission],
  [Discharge Notes::], [#lorem(50)],
)



#text("\n")

#text(16pt,fill: mygray)[*Treating Physician* :] #text(14pt)[#lorem(4)]
#line(length: 100%, stroke: mygray)
