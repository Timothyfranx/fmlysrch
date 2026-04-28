# FamilySearch Oral Genealogy Extraction Prompt

Use the following prompt when sending sheet photos to Claude or ChatGPT for data extraction.

---

## The Prompt

You are helping extract data from a FamilySearch oral genealogy interview sheet.

### Columns to Extract
- **RIN #**: Row number.
- **Relation S/C/P**: Relation code. For children with two parents (e.g., parents are RIN 1 and RIN 2), use the format `C1,C2`. Always prefix each parent number with 'C'.
- **Sex M/F**: Output as "Male" or "Female".
- **Given names, Family names**: Two separate name fields. Use **Sentence Case** (e.g., "Ezinwanne" instead of "EZINWANNE").
- **Birth and Death Section**:
    - **Smiling face icon**: Birth info (year and/or location).
        - If **CIRCLED**: `living = "Yes"`.
    - **Cemetery icon**: Death info (year and/or location).
        - If **CIRCLED**: `living = "No"`.
- **Location**: Format is `Ward, LGA, State, Country`. Use **Sentence Case**.
    - If only a ward name is written, keep the same LGA/State/Country as the base location.
    - `"` (ditto mark) means same location as the row above.
    - Base location for this sheet is written at the top of the page.

### Rules
- If `living = "No"` and no death location is written, set `death_location` to the same as `birth_location`.
- Birth and death are **YEAR ONLY**, never a full date.
- **Relation code**: Use the format `C1` for one parent or `C1,C2` for two parents.
- **Row 1**: Always has an empty relation field — leave it as `""`.
- If a field is unknown or blank, use `null`.
- **Formatting**: Use Sentence Case for all names and locations.

### Output Format
Output **ONLY** a valid JSON array. No explanation, no markdown, no extra text. Use exactly this structure:

```json
[
  {
    "rin": 1,
    "relation": "",
    "sex": "Male",
    "given_names": "Omah",
    "family_names": "Nwanwu",
    "birth_year": null,
    "birth_location": "Onu Ukpoka Mbu Akpoti, Isi Uzo, Enugu, Nigeria",
    "death_year": null,
    "death_location": "Onu Ukpoka Mbu Akpoti, Isi Uzo, Enugu, Nigeria",
    "living": "No"
  }
]
```

---

## Tips for Best Results
- Always verify the **base location** from the top header of the sheet.
- Double check the **circled icon** (smiling vs. cemetery) for every row.
- If a name is unclear, write your best guess — the user will review and correct.
- **Do NOT** add any text before or after the JSON array.
