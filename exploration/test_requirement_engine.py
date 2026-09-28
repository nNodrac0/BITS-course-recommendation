import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.models.student_profile import StudentProfile
from src.engine.requirement_engine import build_eligible_course_set

with open('data/processed/programmes.json', encoding='utf-8') as f:
    programmes = json.load(f)
with open('data/processed/course_pools.json', encoding='utf-8') as f:
    course_pools = json.load(f)
with open('data/processed/handouts.json', encoding='utf-8') as f:
    handouts = json.load(f)

handout_codes = {h['course_code'] for h in handouts if h['course_code'] and not h['is_higher_degree']}
chemical = next(p for p in programmes if p['programme_name'] == 'B.E. Chemical')

# Realistic profile: Year I fully done, Year II sem1 done, Year II sem2 partially
# done (ECON F211 alternative chosen, but CHE F241-244 NOT done - Year III should
# stay gated), one Humanities Elective done via a real pool course
completed = [
    'BITS F103','BIO F101','CHEM F101','MATH F101','PHY F101','BITS F101','BITS K101',
    'BITS F111','BITS F112','CS F111','MATH F113','MATH F102','EEE F111','BITS F102',
    'MATH F211','CHE F211','CHE F214','CHE F213','CHE F212','BITS F225',
    'ECON F211',  # chose this alternative over MGTS F211
    'BITS F214',  # a real Humanities pool course
]
profile = StudentProfile(campus='Pilani', programme_name='B.E. Chemical', admission_year=2023,
                          current_semester=5, completed_courses=completed)

result = build_eligible_course_set('B.E. Chemical', profile, chemical, course_pools, handout_codes)
print('eligible named courses now:')
for g in result['eligible_named_courses']:
    print(' ', g)
print()
print('remaining electives:', result['remaining_electives'])
print()
for cat, codes in result['elective_candidates'].items():
    print(cat, '-> candidate count:', len(codes))