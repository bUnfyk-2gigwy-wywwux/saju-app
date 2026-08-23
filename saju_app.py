# -*- coding: utf-8 -*-
"""
사주팔자 운세 프로그램 (하이브리드 · 생년월일시 기준)
─────────────────────────────────────────────
  1) 규칙 엔진 : 사주 · 오행 · 십성 · 신강/신약 · 일진/월건/세운 · 대운 · 좋은날 · 토정 작괘
  2) AI 해석   : 성격·오행·직업재물 + 대운 + 오늘/주간/월간/올해(금전·사업) + 팁/처세 + 토정 + 조언
  3) 용어 설명 · 학습 모드 · 파일/카톡 텍스트 내보내기

실행
  pip install -r requirements.txt
  streamlit run saju_app.py

※ 운세 결과는 오락·참고용입니다.
"""

import json
import datetime
from pathlib import Path
import pandas as pd
import altair as alt
import streamlit as st
import sxtwl

# ──────────────────────────────────────────────
# 기준 상수
# ──────────────────────────────────────────────
GAN = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
ZHI = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
GAN_HJ = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
ZHI_HJ = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

GAN_ELEM = ['목', '목', '화', '화', '토', '토', '금', '금', '수', '수']
GAN_YIN  = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
ZHI_ELEM = ['수', '토', '목', '목', '토', '화', '화', '토', '금', '금', '토', '수']
ZHI_MAIN_GAN = [9, 5, 0, 1, 4, 2, 3, 5, 6, 7, 4, 8]
SIJIN = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
# 토정 작괘용 선천수(先天數)
GAN_SUN = [9, 8, 7, 6, 5, 9, 8, 7, 6, 5]
ZHI_SUN = [9, 8, 7, 6, 5, 4, 9, 8, 7, 6, 5, 4]
PALGWAE = {1: '건(乾·하늘)', 2: '태(兌·못)', 3: '리(離·불)', 4: '진(震·우레)',
           5: '손(巽·바람)', 6: '감(坎·물)', 7: '간(艮·산)', 8: '곤(坤·땅)'}

ELEM_ORDER = ['목', '화', '토', '금', '수']
ELEM_COLOR = {'목': '🟢', '화': '🔴', '토': '🟡', '금': '⚪', '수': '🔵'}
ELEM_HEX = {'목': '#2e9e5b', '화': '#e2554e', '토': '#e6b422', '금': '#9aa0a6', '수': '#2f6fed'}
SIBSEONG_GROUP = {
    '비견': '비겁', '겁재': '비겁', '식신': '식상', '상관': '식상',
    '편재': '재성', '정재': '재성', '편관': '관성', '정관': '관성',
    '편인': '인성', '정인': '인성',
}
FAVORABLE_SIB = {'식신', '정재', '정관', '정인'}

GLOSSARY = {
    "천간(天干)": "갑을병정무기경신임계 10글자. 하늘의 기운을 나타냅니다.",
    "지지(地支)": "자축인묘진사오미신유술해 12글자. 땅의 기운이자 띠에 해당합니다.",
    "사주(四柱)": "년·월·일·시 네 기둥. 각 기둥은 천간+지지 한 쌍입니다.",
    "일간(日干)·아신(我身)": "태어난 날의 천간으로, 사주의 주인공인 '나'를 상징하는 기준점입니다.",
    "동주(同柱)": "같은 기둥 안에 함께 있는 것(예: 월주 안의 천간과 지지).",
    "오행(五行)": "목·화·토·금·수 다섯 기운. 서로 생(生)하고 극(克)합니다.",
    "신강/신약/중화": "일간을 돕는 힘(비겁·인성)과 빼는 힘(식상·재성·관성)의 균형입니다.",
    "비겁(비견·겁재)": "나와 같은 오행. 경쟁·동료·동업·자존심.",
    "식상(식신·상관)": "내가 생(生)하는 오행. 표현·재능·영업·생산.",
    "재성(정재·편재)": "내가 극(克)하는 오행. 재물·수익·실속(정재=고정수입, 편재=유동·사업자금).",
    "관성(정관·편관)": "나를 극하는 오행. 직위·규율·책임·압박(편관=칠살).",
    "인성(정인·편인)": "나를 생하는 오행. 학문·문서·계약·보호·후원.",
    "정(正)/편(偏)": "음양이 다르면 '정'(안정적), 같으면 '편'(변동적) 경향.",
    "일진(日辰)": "그날 하루의 간지. 오늘의 기운입니다.",
    "월건(月建)": "그달의 간지. 이번 달의 기운입니다.",
    "세운(歲運)": "그해의 간지. 올해 운의 큰 흐름입니다.",
    "대운(大運)": "10년 단위로 바뀌는 운의 큰 줄기. 월주에서 출발해 순행/역행합니다.",
    "대운수": "대운이 시작되는 나이. 출생일에서 절기까지의 날수를 3으로 나눠 정합니다.",
    "순행/역행": "양남음녀는 순행, 음남양녀는 역행으로 대운이 진행됩니다.",
    "상괘·중괘·하괘": "토정비결 작괘 시 위·가운데·아래 세 숫자로, 합쳐 그해 괘를 정합니다.",
}

MODEL_OPTIONS = {
    "Sonnet 4.6 (균형·기본 추천)": "claude-sonnet-4-6",
    "Opus 4.8 (가장 정교·약 1.7배 비용)": "claude-opus-4-8",
    "Haiku 4.5 (가장 저렴·빠름)": "claude-haiku-4-5-20251001",
}
DEFAULT_MODEL_LABEL = "Sonnet 4.6 (균형·기본 추천)"
LAST_FILE = Path(__file__).with_name("saju_last.json")


def load_last_subject():
    try:
        return json.loads(LAST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_last_subject(data):
    try:
        LAST_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _sheng(a, b):
    return ELEM_ORDER[(ELEM_ORDER.index(a) + 1) % 5] == b


def _ke(a, b):
    return ELEM_ORDER[(ELEM_ORDER.index(a) + 2) % 5] == b


def ten_god(dg, tg):
    se, sy = GAN_ELEM[dg], GAN_YIN[dg]
    te, ty = GAN_ELEM[tg], GAN_YIN[tg]
    same = (sy == ty)
    if te == se:
        return '비견' if same else '겁재'
    if _sheng(se, te):
        return '식신' if same else '상관'
    if _ke(se, te):
        return '편재' if same else '정재'
    if _ke(te, se):
        return '편관' if same else '정관'
    if _sheng(te, se):
        return '편인' if same else '정인'
    return '?'


def explain_sib(dg, tg):
    se, sy = GAN_ELEM[dg], GAN_YIN[dg]
    te, ty = GAN_ELEM[tg], GAN_YIN[tg]
    if te == se:
        rel = f"일간과 같은 오행({te})"
    elif _sheng(se, te):
        rel = f"일간 {se}가 {te}를 생(生)"
    elif _ke(se, te):
        rel = f"일간 {se}가 {te}를 극(克)"
    elif _ke(te, se):
        rel = f"{te}가 일간 {se}를 극(克)"
    else:
        rel = f"{te}가 일간 {se}를 생(生)"
    return f"{rel}, 음양 {'같음' if sy == ty else '다름'} → **{ten_god(dg, tg)}**"


def learning_rows(s):
    dg = s['day_gan_idx']
    rows = []
    for k in ['년', '월', '일', '시']:
        if k not in s['pillars']:
            continue
        p = s['pillars'][k]
        if k == '일':
            rows.append((f"{k}주 천간 {GAN[p['gan']]}", "일간(我身) — 모든 비교의 기준입니다."))
        else:
            rows.append((f"{k}주 천간 {GAN[p['gan']]}", explain_sib(dg, p['gan'])))
        mg = ZHI_MAIN_GAN[p['zhi']]
        rows.append((f"{k}주 지지 {ZHI[p['zhi']]}(본기 {GAN[mg]})", explain_sib(dg, mg)))
    return rows


def _gz60_index(g, z):
    for n in range(60):
        if n % 10 == g and n % 12 == z:
            return n
    return 0


# ──────────────────────────────────────────────
# 규칙 기반 엔진
# ──────────────────────────────────────────────
def compute_saju(year, month, day, hour=None, minute=0, is_lunar=False, is_leap=False):
    if is_lunar:
        d = sxtwl.fromLunar(year, month, day, is_leap)
    else:
        d = sxtwl.fromSolar(year, month, day)
    time_known = hour is not None
    raw = {'년': d.getYearGZ(), '월': d.getMonthGZ(), '일': d.getDayGZ()}
    if time_known:
        raw['시'] = d.getHourGZ(hour)
    day_gan = raw['일'].tg

    pillars = {}
    for k, gz in raw.items():
        pillars[k] = {
            'gan': gz.tg, 'zhi': gz.dz,
            'han': GAN[gz.tg] + ZHI[gz.dz], 'hanja': GAN_HJ[gz.tg] + ZHI_HJ[gz.dz],
            'gan_sib': '일간(我身)' if k == '일' else ten_god(day_gan, gz.tg),
            'zhi_sib': ten_god(day_gan, ZHI_MAIN_GAN[gz.dz]),
        }

    elem = {e: 0 for e in ELEM_ORDER}
    for gz in raw.values():
        elem[GAN_ELEM[gz.tg]] += 1
        elem[ZHI_ELEM[gz.dz]] += 1

    groups = {'비겁': 0, '식상': 0, '재성': 0, '관성': 0, '인성': 0}
    for k, pp in pillars.items():
        if k != '일':
            groups[SIBSEONG_GROUP[pp['gan_sib']]] += 1
        groups[SIBSEONG_GROUP[pp['zhi_sib']]] += 1

    support = groups['비겁'] + groups['인성']
    drain = groups['식상'] + groups['재성'] + groups['관성']
    strength = '신강' if support >= drain + 2 else ('신약' if drain >= support + 2 else '중화')

    return {
        'pillars': pillars, 'elem': elem, 'groups': groups, 'strength': strength,
        'day_gan': GAN[day_gan], 'day_gan_idx': day_gan,
        'day_elem': GAN_ELEM[day_gan], 'day_yin': '양' if GAN_YIN[day_gan] == 0 else '음',
        'month_gan': raw['월'].tg, 'month_zhi': raw['월'].dz,
        'year_gan': raw['년'].tg,
        'sijin': SIJIN[(hour + 1) // 2 % 12] if time_known else None,
        'time_known': time_known,
    }


def rule_based_summary(s):
    elem = s['elem']
    most = max(elem, key=elem.get)
    least = [e for e, v in elem.items() if v == 0]
    lines = [
        f"**일간(나)**: {s['day_gan']}({s['day_elem']}·{s['day_yin']})",
        f"**신강/신약(참고)**: {s['strength']}"
        + ("" if s['time_known'] else " · 시각 미상이라 시주 제외(정밀도 다소 낮음)"),
        f"**오행 우세**: {most}({elem[most]}개)"
        + (f" / **부재 오행**: {', '.join(least)}" if least else " / 부재 오행 없음"),
    ]
    if s['strength'] == '신강':
        hint = "일간이 강한 편 → 식상·재성·관성으로 기운을 흘려보내는 방향 참고"
    elif s['strength'] == '신약':
        hint = "일간이 약한 편 → 인성·비겁으로 일간을 돕는 방향 참고"
    else:
        hint = "기운이 비교적 균형 → 부재·약한 오행을 보완하는 방향 참고"
    lines.append(f"**보완 방향(참고)**: {hint}")
    return "\n\n".join(lines)


def elem_chart(s):
    df = pd.DataFrame({"오행": ELEM_ORDER, "개수": [s['elem'][e] for e in ELEM_ORDER]})
    return (
        alt.Chart(df).mark_bar().encode(
            x=alt.X("오행:N", sort=ELEM_ORDER,
                    axis=alt.Axis(labelAngle=0, title=None, labelFontSize=15)),
            y=alt.Y("개수:Q", axis=alt.Axis(title="개수", tickMinStep=1)),
            color=alt.Color("오행:N", sort=ELEM_ORDER, legend=None,
                            scale=alt.Scale(domain=ELEM_ORDER,
                                            range=[ELEM_HEX[e] for e in ELEM_ORDER])),
        ).properties(height=240)
    )


def _gz_info(dg, gz):
    return {'han': GAN[gz.tg] + ZHI[gz.dz], 'hanja': GAN_HJ[gz.tg] + ZHI_HJ[gz.dz],
            'gan_sib': ten_god(dg, gz.tg), 'zhi_sib': ten_god(dg, ZHI_MAIN_GAN[gz.dz])}


def luck_context(s, today=None):
    today = today or datetime.date.today()
    d = sxtwl.fromSolar(today.year, today.month, today.day)
    g = s['day_gan_idx']
    return {'date': today.isoformat(), 'year_num': today.year,
            'day': _gz_info(g, d.getDayGZ()), 'month': _gz_info(g, d.getMonthGZ()),
            'year': _gz_info(g, d.getYearGZ())}


def good_days(s, n=45, count=5, today=None):
    today = today or datetime.date.today()
    g = s['day_gan_idx']
    out = []
    for i in range(n):
        dt = today + datetime.timedelta(days=i)
        gz = sxtwl.fromSolar(dt.year, dt.month, dt.day).getDayGZ()
        sib = ten_god(g, gz.tg)
        if sib in FAVORABLE_SIB:
            out.append({'date': dt.isoformat(), 'wd': '월화수목금토일'[dt.weekday()],
                        'gz': GAN[gz.tg] + ZHI[gz.dz], 'sib': sib})
        if len(out) >= count:
            break
    return out


def _days_to_jie(base, forward):
    step = 1 if forward else -1
    cur, cnt = base, 0
    for _ in range(200):
        cur += datetime.timedelta(days=step)
        cnt += 1
        d = sxtwl.fromSolar(cur.year, cur.month, cur.day)
        if d.hasJieQi() and d.getJieQi() % 2 == 1:  # 節(월 경계)
            return cnt
    return cnt


def major_luck(s, year, month, day, is_lunar, is_leap, gender, today=None):
    """대운: 순행/역행 · 대운수 · 10년 주기 간지(월주 기준)."""
    today = today or datetime.date.today()
    d = sxtwl.fromLunar(year, month, day, is_leap) if is_lunar else sxtwl.fromSolar(year, month, day)
    yg, mg = d.getYearGZ(), d.getMonthGZ()
    base = datetime.date(d.getSolarYear(), d.getSolarMonth(), d.getSolarDay())
    yang = (GAN_YIN[yg.tg] == 0)
    male = (gender == '남성')
    forward = (yang and male) or ((not yang) and (not male))
    dae_num = max(1, round(_days_to_jie(base, forward) / 3))
    g = s['day_gan_idx']
    m_idx = _gz60_index(mg.tg, mg.dz)
    seq = []
    for i in range(1, 9):
        n = (m_idx + i) % 60 if forward else (m_idx - i) % 60
        seq.append({'age': dae_num + (i - 1) * 10,
                    'gz': GAN[n % 10] + ZHI[n % 12], 'sib': ten_god(g, n % 10)})
    cur_age = today.year - year + 1
    if cur_age < dae_num:
        current = None
    else:
        idx = (cur_age - dae_num) // 10
        current = seq[idx] if idx < len(seq) else seq[-1]
    return {'forward': forward, 'dae_num': dae_num, 'wol': GAN[mg.tg] + ZHI[mg.dz],
            'seq': seq, 'current': current, 'cur_age': cur_age}


def tojeong_gua(year, month, day, is_lunar, is_leap, today=None):
    """선천수 기반 정통 작괘 공식(상8·중6·하3진). ※정통 조견표와 일부 차이 가능."""
    today = today or datetime.date.today()
    d = sxtwl.fromLunar(year, month, day, is_leap) if is_lunar else sxtwl.fromSolar(year, month, day)
    ly, lm, ld = d.getLunarYear(), d.getLunarMonth(), d.getLunarDay()
    leap = d.isLunarLeap()
    cy = today.year
    yg = sxtwl.fromSolar(cy, 6, 1).getYearGZ()
    age = cy - ly + 1
    tae = GAN_SUN[yg.tg] + ZHI_SUN[yg.dz]          # 태세수(올해)
    sang = (age + tae) % 8 or 8
    try:
        dsize = sxtwl.getLunarMonthNum(cy, lm, leap)
    except Exception:
        dsize = 30
    mg = sxtwl.fromLunar(cy, lm, min(15, dsize), leap).getMonthGZ()
    wgun = GAN_SUN[mg.tg] + ZHI_SUN[mg.dz]         # 월건수
    jung = (dsize + wgun) % 6 or 6
    dg = d.getDayGZ()
    iljin = GAN_SUN[dg.tg] + ZHI_SUN[dg.dz]        # 일진수(생일)
    ha = (ld + iljin) % 3 or 3
    return {'lunar': f"{ly}년 {lm}월 {ld}일", 'age': age,
            'sang': sang, 'jung': jung, 'ha': ha, 'gua': f"{sang}{jung}{ha}",
            'sang_name': PALGWAE[sang], 'year_gz': GAN[yg.tg] + ZHI[yg.dz]}


# ──────────────────────────────────────────────
# AI 해석
# ──────────────────────────────────────────────
def build_prompt(s, gender, birth_label, luck, dae, toj, ref_label, is_today):
    p = s['pillars']
    table = "\n".join(
        f"- {k}주: {p[k]['han']}({p[k]['hanja']}) | 천간 {p[k]['gan_sib']} | 지지 {p[k]['zhi_sib']}"
        for k in ['년', '월', '일', '시'] if k in p)
    if not s['time_known']:
        table += "\n- 시주: 미상(출생 시각 모름 → 시주 제외)"
    elem_line = ", ".join(f"{e} {s['elem'][e]}개" for e in ELEM_ORDER)
    group_line = ", ".join(f"{g} {s['groups'][g]}개" for g in s['groups'])
    y = luck['year_num']
    pd_, pw, pm, py_ = ("오늘", "이번 주", "이번 달", "올해") if is_today else ("기준일", "해당 주", "해당 달", "해당 연도")
    cur = dae['current']
    cur_line = (f"{cur['gz']}({cur['sib']}), {cur['age']}세부터" if cur else "대운 시작 전(유년기)")
    dae_seq = " → ".join(f"{x['age']}세 {x['gz']}({x['sib']})" for x in dae['seq'][:6])
    return f"""당신은 한국 전통 명리학(사주팔자)·토정비결에 정통한 상담가입니다.
아래는 규칙 기반 엔진이 정확히 산출한 데이터입니다. 수치를 임의로 바꾸지 말고 해석만 하십시오.
시간 관련(대운·{pd_}·{pw}·{pm}·{py_}) 항목은 '금전·사업·재물' 방향을 중심에 두고 즉시 실행 가능하게 쓰십시오.
모든 시간 항목은 아래 [조회 기준일]을 기준으로 작성하고, 다른 시점을 임의로 말하지 마십시오.

[대상자] {birth_label} / 성별: {gender}
[조회 기준일] {ref_label}
[사주 원국]
{table}
[일간] {s['day_gan']}({s['day_elem']}·{s['day_yin']}) / [신강·신약] {s['strength']}
[오행 분포] {elem_line}
[십성 분포] {group_line}

[대운] {'순행' if dae['forward'] else '역행'} · 대운수 {dae['dae_num']} · {py_} 대운 {cur_line}
[대운 흐름] {dae_seq}
[{pd_} 일진] {luck['day']['han']} · 천간십성 {luck['day']['gan_sib']} (날짜 {luck['date']})
[{pm} 월건] {luck['month']['han']} · 천간십성 {luck['month']['gan_sib']}
[{py_} 세운] {luck['year']['han']} · 천간십성 {luck['year']['gan_sib']} ({y}년)
[간이 토정 작괘] {toj['gua']}괘 (上{toj['sang']} 中{toj['jung']} 下{toj['ha']}, 상괘 {toj['sang_name']}) · 세는나이 {toj['age']} · 음력생일 {toj['lunar']}

참고(십성↔금전·사업): 재성=직접 재물·수익, 관성=직위·계약이행·사업관리, 식상=영업·생산·아이디어 수익화, 비겁=경쟁·동업·자금분산, 인성=문서·계약·투자판단.

아래 형식의 마크다운으로, 각 항목 2~4문장씩 한국어 격식체(~합니다)로 작성하십시오.
과장·미신적 단정은 피하고, 경향성과 실행 조언 위주로 쓰십시오.

## 총평
## 성격과 기질
## 오행 균형과 보완 방향
## 직업·재물 경향
## 대운 흐름 (10년 주기)
## {pd_}의 운세 — 금전·사업
## {pd_} 팁 & 처세
## {pw} 흐름 — 금전·사업
## {pm} 흐름 — 금전·사업
## {py_} 흐름 — 금전·사업 ({y}년)
## 종합 금전·사업 방향
## 토정비결 — {y}년 총운 (간이·오락용)
## 조언 한마디

마지막에 "※ 본 해석은 오락·참고용이며, 토정비결은 정통 144괘 원문이 아닌 간이 작괘 기반입니다." 한 줄을 덧붙이십시오."""


def ai_interpretation(s, gender, birth_label, luck, dae, toj, ref_label, is_today, api_key, model):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model, max_tokens=8000,
        messages=[{"role": "user",
                   "content": build_prompt(s, gender, birth_label, luck, dae, toj, ref_label, is_today)}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


# ──────────────────────────────────────────────
# 결과 리포트(저장·복사용)
# ──────────────────────────────────────────────
def build_report(s, birth_label, gender, luck, dae, good, toj, ai_text):
    p = s['pillars']
    L = ["# 사주팔자 운세 결과", "", f"- 대상자: {birth_label} · {gender}",
         f"- 생성일: {luck['date']}", "", "## 사주 원국"]
    for k in ['년', '월', '일', '시']:
        if k in p:
            L.append(f"- {k}주: {p[k]['han']}({p[k]['hanja']}) · 천간 {p[k]['gan_sib']} · 지지 {p[k]['zhi_sib']}")
    if not s['time_known']:
        L.append("- 시주: 미상")
    L += [f"- 일간: {s['day_gan']}({s['day_elem']}·{s['day_yin']}) / 신강·신약: {s['strength']}", "",
          "## 오행 분포", ", ".join(f"{e} {s['elem'][e]}개" for e in ELEM_ORDER), "",
          "## 규칙 기반 요약", rule_based_summary(s).replace("**", ""), "",
          "## 대운 (10년 주기)",
          f"- 방향: {'순행' if dae['forward'] else '역행'} · 대운수: {dae['dae_num']}"]
    L += [f"- {x['age']}세: {x['gz']} ({x['sib']})" for x in dae['seq']]
    L += ["", "## 간지 흐름 (기준일 기준)",
          f"- 일진({luck['date']}): {luck['day']['han']} ({luck['day']['gan_sib']})",
          f"- 월건: {luck['month']['han']} ({luck['month']['gan_sib']})",
          f"- 세운({luck['year_num']}년): {luck['year']['han']} ({luck['year']['gan_sib']})", "",
          "## 좋은 날 (간이 택일)"]
    L += [f"- {gd['date']}({gd['wd']}) · {gd['gz']}일 · 길신 {gd['sib']}" for gd in good] or ["- 해당 길일 없음"]
    L += ["", "## 토정비결 작괘 (간이·오락용)",
          f"- 올해 괘: {toj['gua']}괘 (上{toj['sang']} 中{toj['jung']} 下{toj['ha']}, 상괘 {toj['sang_name']}) · 세는나이 {toj['age']}", ""]
    if ai_text:
        L += ["## AI 운세 해석", ai_text, ""]
    L += ["---", "※ 본 결과는 오락·참고용입니다. 좋은날·토정비결은 간이 버전입니다."]
    return "\n".join(L)


def to_plaintext(report_md):
    out = []
    for line in report_md.splitlines():
        l = line.replace('**', '')
        if l.startswith('## '):
            l = '■ ' + l[3:]
        elif l.startswith('# '):
            l = '【' + l[2:] + '】'
        elif l.startswith('- '):
            l = '· ' + l[2:]
        out.append(l)
    return '\n'.join(out)


# ──────────────────────────────────────────────
# 궁합 엔진 (2인 비교)
# ──────────────────────────────────────────────
YUKHAP = [{0, 1}, {2, 11}, {3, 10}, {4, 9}, {5, 8}, {6, 7}]
SAMHAP = [{2, 6, 10}, {8, 0, 4}, {5, 9, 1}, {11, 3, 7}]
WONJIN = [{0, 7}, {1, 6}, {2, 9}, {3, 8}, {4, 11}, {5, 10}]


def _stem_relation(a, b):
    if abs(a - b) == 5:
        return ('천간합', 1.0)
    ea, eb = GAN_ELEM[a], GAN_ELEM[b]
    if ea == eb:
        return ('비화', 0.5)
    if _sheng(ea, eb) or _sheng(eb, ea):
        return ('상생', 0.85)
    return ('상극', 0.25)


def _branch_relation(a, b):
    if a == b:
        return ('동지', 0.55)
    s = {a, b}
    if s in YUKHAP:
        return ('육합', 1.0)
    if any(s <= g for g in SAMHAP):
        return ('삼합', 0.9)
    if abs(a - b) == 6:
        return ('충', 0.15)
    if s in WONJIN:
        return ('원진', 0.2)
    return ('무관', 0.5)


def _ohaeng_comp(a, b):
    defi = [e for e in ELEM_ORDER if a['elem'][e] <= 1]
    if not defi:
        return 1.0
    return sum(1 for e in defi if b['elem'][e] >= 1) / len(defi)


def _needed_elem(s):
    i = ELEM_ORDER.index(s['day_elem'])
    if s['strength'] == '신약':
        return {s['day_elem'], ELEM_ORDER[(i - 1) % 5]}
    if s['strength'] == '신강':
        return {ELEM_ORDER[(i + 1) % 5], ELEM_ORDER[(i + 2) % 5]}
    return {e for e in ELEM_ORDER if s['elem'][e] <= 1}


def _yong_exchange(a, b):
    nd = _needed_elem(a)
    return min(1.0, sum(b['elem'][e] for e in nd) / 4.0)


def compatibility(s1, s2):
    il_l, il = _stem_relation(s1['day_gan_idx'], s2['day_gan_idx'])
    ij_l, ij = _branch_relation(s1['pillars']['일']['zhi'], s2['pillars']['일']['zhi'])
    oh = (_ohaeng_comp(s1, s2) + _ohaeng_comp(s2, s1)) / 2
    tt_l, tt = _branch_relation(s1['pillars']['년']['zhi'], s2['pillars']['년']['zhi'])
    yo = (_yong_exchange(s1, s2) + _yong_exchange(s2, s1)) / 2
    raw = {'일간': il, '일지': ij, '오행보완': oh, '띠': tt, '용신교류': yo}
    WL = {'일간': .30, '일지': .30, '오행보완': .15, '띠': .15, '용신교류': .10}
    WB = {'일간': .20, '일지': .10, '오행보완': .30, '띠': .10, '용신교류': .30}
    return {'raw': raw, 'labels': {'일간': il_l, '일지': ij_l, '띠': tt_l},
            'love': round(sum(raw[k] * WL[k] for k in raw) * 100),
            'biz': round(sum(raw[k] * WB[k] for k in raw) * 100)}


def compat_grade(x):
    return '상 (잘 맞음)' if x >= 75 else '중상 (대체로 좋음)' if x >= 60 else '중 (보통)' if x >= 45 else '주의 (보완 필요)'


def compat_notes(c):
    good, caution = [], []
    L, r = c['labels'], c['raw']
    if L['일간'] in ('천간합', '상생'):
        good.append(f"일간이 {L['일간']} 관계로 끌림·소통이 자연스럽습니다.")
    elif L['일간'] == '상극':
        caution.append("일간이 상극이라 가치관·주도권에서 마찰이 생길 수 있습니다.")
    if L['일지'] in ('육합', '삼합'):
        good.append(f"일지가 {L['일지']}으로 생활·정서의 결이 잘 맞습니다.")
    elif L['일지'] in ('충', '원진'):
        caution.append(f"일지가 {L['일지']} 관계라 가까울수록 생활 갈등을 관리해야 합니다.")
    if r['오행보완'] >= 0.6:
        good.append("서로 부족한 오행을 채워 주는 보완 관계입니다.")
    elif r['오행보완'] <= 0.3:
        caution.append("오행이 비슷해 강점·약점이 겹칠 수 있습니다.")
    if L['띠'] in ('육합', '삼합'):
        good.append(f"띠가 {L['띠']}으로 인연의 결이 좋은 편입니다.")
    elif L['띠'] in ('충', '원진'):
        caution.append(f"띠가 {L['띠']}이라 초반 리듬·인상 차이가 있을 수 있습니다.")
    if r['용신교류'] >= 0.5:
        good.append("상대가 내게 필요한 기운(용신)을 보태 주는 편입니다.")
    return (good or ["두드러진 강점은 약하나 무난한 편입니다."],
            caution or ["크게 주의할 충돌 요인은 적습니다."])


def build_compat_report(cp):
    c, meta, persp = cp['c'], cp['meta'], cp['persp']
    good, caution = compat_notes(c)
    L = ["# 궁합 결과", "", f"- 본인: {meta['본인']}", f"- 상대: {meta['상대']}",
         f"- 관점: {persp}", "", "## 종합 등급"]
    if persp in ('연애', '둘 다'):
        L.append(f"- 연애 궁합: {c['love']}점 ({compat_grade(c['love'])})")
    if persp in ('동업', '둘 다'):
        L.append(f"- 동업 궁합: {c['biz']}점 ({compat_grade(c['biz'])})")
    L += ["", "## 지표별 관계",
          f"- 일간: {c['labels']['일간']}", f"- 일지: {c['labels']['일지']}",
          f"- 띠: {c['labels']['띠']}",
          f"- 오행 보완: {round(c['raw']['오행보완'] * 100)}%",
          f"- 용신 교류: {round(c['raw']['용신교류'] * 100)}%", "", "## 잘 맞는 점"]
    L += [f"- {g}" for g in good]
    L += ["", "## 주의·보완할 점"] + [f"- {x}" for x in caution]
    L += ["", "---", "※ 궁합은 경향성 참고용(오락)이며 관계를 단정하지 않습니다."]
    return "\n".join(L)


def render_compat():
    st.subheader("💞 궁합 보기 (2인)")
    persp = st.radio("관점", ["연애", "동업", "둘 다"], horizontal=True, key="cp_persp")
    people = {}
    cols = st.columns(2)
    for label, col, pf in [("본인", cols[0], "a"), ("상대", cols[1], "b")]:
        with col:
            st.markdown(f"**{label}**")
            cal = st.radio("달력", ["양력", "음력"], horizontal=True, key=f"cp_cal_{pf}")
            bd = st.date_input("생년월일", value=datetime.date(1990, 1, 1),
                               min_value=datetime.date(1900, 1, 1),
                               max_value=datetime.date(2100, 12, 31), key=f"cp_date_{pf}")
            leap = st.checkbox("윤달", key=f"cp_leap_{pf}") if cal == "음력" else False
            unk = st.checkbox("출생 시각 모름", key=f"cp_unk_{pf}")
            tm = st.time_input("출생 시각", value=datetime.time(12, 0), disabled=unk, key=f"cp_time_{pf}")
            gd = st.radio("성별", ["남성", "여성"], horizontal=True, key=f"cp_gender_{pf}")
            people[label] = (cal, bd, leap, unk, tm, gd)
    st.caption("ℹ️ 상대방 정보는 동의 하에 입력해 주세요. 결과는 경향성 참고용입니다.")

    if st.button("궁합 보기", type="primary", use_container_width=True):
        try:
            ss, meta = {}, {}
            for label, (cal, bd, leap, unk, tm, gd) in people.items():
                hour = None if unk else tm.hour
                ss[label] = compute_saju(bd.year, bd.month, bd.day, hour,
                                         0 if unk else tm.minute,
                                         is_lunar=(cal == "음력"), is_leap=leap)
                t_part = "시각미상" if unk else f"{tm.hour:02d}:{tm.minute:02d}"
                meta[label] = f"{cal} {bd.year}.{bd.month}.{bd.day} {t_part} · {gd}"
            st.session_state["compat"] = {
                "s1": ss["본인"], "s2": ss["상대"],
                "c": compatibility(ss["본인"], ss["상대"]),
                "meta": meta, "persp": persp}
        except Exception as e:
            st.error(f"계산 중 오류가 발생했습니다: {e}")

    if "compat" in st.session_state:
        cp = st.session_state["compat"]
        s1, s2, c = cp["s1"], cp["s2"], cp["c"]
        good, caution = compat_notes(c)

        st.markdown("### 📜 두 사람 원국")
        for col, (label, s) in zip(st.columns(2), [("본인", s1), ("상대", s2)]):
            with col:
                st.markdown(f"**{label}** · {cp['meta'][label]}")
                st.write(f"· 일간 {s['day_gan']}({s['day_elem']}·{s['day_yin']}) / {s['strength']}")
                st.write(f"· 일주 {s['pillars']['일']['han']}")
                st.write("· 오행 " + ", ".join(f"{e}{s['elem'][e]}" for e in ELEM_ORDER))

        st.markdown("### 💞 궁합 종합 등급")
        if cp["persp"] in ("연애", "둘 다"):
            st.write(f"- **연애 궁합**: {c['love']}점 · {compat_grade(c['love'])}")
        if cp["persp"] in ("동업", "둘 다"):
            st.write(f"- **동업 궁합**: {c['biz']}점 · {compat_grade(c['biz'])}")

        st.markdown("### 📊 지표별 관계")
        rows = [["일간 (끌림·소통)", c['labels']['일간']],
                ["일지 (생활·정서)", c['labels']['일지']],
                ["띠 (인연 결)", c['labels']['띠']],
                ["오행 보완", f"{round(c['raw']['오행보완'] * 100)}%"],
                ["용신 교류", f"{round(c['raw']['용신교류'] * 100)}%"]]
        st.table(pd.DataFrame(rows, columns=["지표", "관계 / 점수"]))

        st.markdown("### 🟢 잘 맞는 점")
        for g in good:
            st.write(f"- {g}")
        st.markdown("### 🟠 주의·보완할 점")
        for x in caution:
            st.write(f"- {x}")

        rep = build_compat_report(cp)
        st.markdown("### 📤 결과 저장·공유")
        st.download_button("📥 궁합 결과 저장 (.md)", data=rep, file_name="궁합결과.md",
                           mime="text/markdown", use_container_width=True)
        with st.expander("💬 카톡·문자용 텍스트 복사"):
            st.code(to_plaintext(rep))
        st.info("더 깊은 궁합 해석(일간합·일지충·용신교류·신살 통변)은 위 결과를 복사해 "
                "**명리 통변실** 프로젝트에 붙여넣으세요.")


# ──────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────
def _app_password():
    try:
        return st.secrets.get("APP_PASSWORD", "")
    except Exception:
        return ""


def check_password():
    """접속 비밀번호. 시크릿 APP_PASSWORD가 있으면 잠금, 없으면 개방(로컬/미설정)."""
    pw = _app_password()
    if not pw:
        return True
    if st.session_state.get("auth_ok"):
        return True
    st.title("🔒 사주 운세 — 접속")
    st.text_input("접속 비밀번호", type="password", key="pw_input")
    if st.button("입장", type="primary"):
        if st.session_state.get("pw_input") == pw:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    st.caption("담당자에게 받은 접속 비밀번호를 입력하세요.")
    return False


def main():
    st.set_page_config(page_title="사주팔자 운세", page_icon="🔮", layout="centered")
    if not check_password():
        st.stop()
    st.title("🔮 사주팔자 운세 (하이브리드)")
    st.caption("규칙 기반 만세력 + 대운 + AI 운세(금전·사업) · 생년월일시 기준 · 오락/참고용")

    with st.sidebar:
        st.subheader("⚙️ 설정")
        api_key = st.text_input("Anthropic API Key", type="password",
                                help="입력하면 AI 운세 해석이 활성화됩니다. 없으면 규칙 기반 결과만 제공됩니다.").strip()
        st.markdown("---")
        model_label = st.selectbox(
            "AI 모델", list(MODEL_OPTIONS.keys()),
            index=list(MODEL_OPTIONS).index(DEFAULT_MODEL_LABEL),
            help="해석 품질과 비용이 달라집니다. Opus가 가장 정교하지만 비용이 약 1.7배입니다.")
        model = MODEL_OPTIONS[model_label]
        st.caption(f"선택된 모델: `{model}`")
        st.markdown("---")
        learning = st.checkbox("🎓 학습 모드", value=False,
                               help="십성·신강신약이 어떻게 계산됐는지 단계별로 보여줍니다.")

    mode = st.radio("모드", ["개인 사주", "궁합(2인)"], horizontal=True)
    if mode == "궁합(2인)":
        render_compat()
        st.markdown("---")
        st.caption("※ 궁합은 경향성 참고용입니다. 관계를 단정하지 않으며, 상대방 정보는 동의 하에 입력하세요.")
        return

    last = load_last_subject()
    if last:
        st.caption(f"🕘 최근 입력 대상자: {last.get('label', '')}")
    d_date = (datetime.date(last['year'], last['month'], last['day']) if last
              else datetime.date(1990, 5, 15))
    d_time = (datetime.time(last.get('hour', 14), last.get('minute', 0)) if last
              else datetime.time(14, 0))
    d_cal_idx = ["양력", "음력"].index(last['cal']) if last else 0
    d_gender_idx = ["남성", "여성"].index(last['gender']) if last else 0
    d_unknown = bool(last.get('time_unknown')) if last else False

    col1, col2 = st.columns(2)
    with col1:
        cal = st.radio("달력", ["양력", "음력"], horizontal=True, index=d_cal_idx)
        bdate = st.date_input("생년월일", value=d_date,
                              min_value=datetime.date(1900, 1, 1),
                              max_value=datetime.date(2100, 12, 31))
        is_leap = st.checkbox("윤달", value=bool(last.get('is_leap')) if last else False) if cal == "음력" else False
    with col2:
        time_unknown = st.checkbox("출생 시각 모름", value=d_unknown,
                                   help="체크하면 시주를 제외하고 년·월·일 3주로 계산합니다.")
        btime = st.time_input("출생 시각", value=d_time, disabled=time_unknown)
        gender = st.radio("성별", ["남성", "여성"], horizontal=True, index=d_gender_idx)

    today = datetime.date.today()
    target_date = st.date_input(
        "📅 조회 기준일 (이 날짜 기준으로 일·주·월·연 흐름과 토정 총운을 봅니다)",
        value=today, min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(2100, 12, 31),
        help="오늘이 아닌 다른 날/달/연도를 고르면 그 시점 기준으로 운세 흐름이 계산됩니다. 기본값은 오늘입니다.")

    if time_unknown:
        st.caption("ℹ️ 출생 시각 모름 → 시주 제외, 년·월·일 3주로 계산(정밀도 다소 낮음). 단 대운·토정은 정상 계산됩니다.")
    else:
        st.caption("ℹ️ 출생 시각은 시주(時柱)에 반영됩니다. 23:00~23:59는 자시(子時)로 계산됩니다.")

    if st.button("사주 계산하기", type="primary", use_container_width=True):
        try:
            hour = None if time_unknown else btime.hour
            minute = 0 if time_unknown else btime.minute
            s = compute_saju(bdate.year, bdate.month, bdate.day, hour, minute,
                             is_lunar=(cal == "음력"), is_leap=is_leap)
            t_part = "시각 미상" if time_unknown else f"{btime.hour:02d}:{btime.minute:02d}"
            birth_label = f"{cal} {bdate.year}년 {bdate.month}월 {bdate.day}일 {t_part}"
            st.session_state["saju"] = s
            st.session_state["meta"] = (birth_label, gender)
            st.session_state["extra"] = {
                "luck": luck_context(s, today=target_date),
                "good": good_days(s, today=target_date),
                "dae": major_luck(s, bdate.year, bdate.month, bdate.day, cal == "음력", is_leap, gender, today=target_date),
                "toj": tojeong_gua(bdate.year, bdate.month, bdate.day, cal == "음력", is_leap, today=target_date),
                "ref": target_date.isoformat(),
                "is_today": (target_date == today),
            }
            st.session_state["ai_result"] = None
            save_last_subject({
                "cal": cal, "year": bdate.year, "month": bdate.month, "day": bdate.day,
                "hour": btime.hour, "minute": btime.minute, "is_leap": bool(is_leap),
                "time_unknown": bool(time_unknown), "gender": gender,
                "label": f"{birth_label} · {gender}"})
        except Exception as e:
            st.error(f"계산 중 오류가 발생했습니다: {e}")

    if "saju" in st.session_state:
        s = st.session_state["saju"]
        birth_label, gender = st.session_state["meta"]
        extra = st.session_state["extra"]
        luck, good, dae, toj = extra["luck"], extra["good"], extra["dae"], extra["toj"]
        ref, is_today = extra.get("ref", luck['date']), extra.get("is_today", True)
        pd_, pw, pm, py_ = ("오늘", "이번 주", "이번 달", "올해") if is_today else ("기준일", "해당 주", "해당 달", "해당 연도")

        st.markdown("### 📜 사주 원국")
        p = s['pillars']
        for c, k in zip(st.columns(4), ['시', '일', '월', '년']):
            with c:
                st.markdown(f"**{k}주**")
                if k in p:
                    st.markdown(f"## {p[k]['hanja']}")
                    st.markdown(p[k]['han'])
                    st.caption(f"천간 {p[k]['gan_sib']}")
                    st.caption(f"지지 {p[k]['zhi_sib']}")
                else:
                    st.markdown("## —")
                    st.caption("시각 미상")

        st.markdown("### 🌈 오행 분포")
        ec1, ec2 = st.columns([2, 1])
        with ec1:
            st.altair_chart(elem_chart(s), use_container_width=True)
        with ec2:
            for e in ELEM_ORDER:
                st.write(f"{ELEM_COLOR[e]} {e} : {s['elem'][e]}개")

        st.markdown("### 🧭 규칙 기반 요약 (즉시 산출)")
        st.info(rule_based_summary(s))

        with st.expander("📖 용어 설명 (신강·십성·대운·일진·세운·토정 등) — 펼치기"):
            for term, desc in GLOSSARY.items():
                st.markdown(f"- **{term}**: {desc}")

        if learning:
            st.markdown("### 🎓 학습 모드 — 십성이 어떻게 나왔나")
            st.caption("오행 생극(生克)과 음양으로 십성이 정해집니다. 일간을 기준으로 각 글자를 비교합니다.")
            for label, exp in learning_rows(s):
                st.markdown(f"- **{label}**: {exp}")
            g = s['groups']
            sup = g['비겁'] + g['인성']
            dr = g['식상'] + g['재성'] + g['관성']
            st.markdown(
                f"**신강·신약 판정 근거**: 돕는 세력(비겁 {g['비겁']}+인성 {g['인성']}={sup}) "
                f"vs 빼는 세력(식상 {g['식상']}+재성 {g['재성']}+관성 {g['관성']}={dr}) "
                f"→ **{s['strength']}**  *(차이 2 이상이면 신강/신약, 그 외 중화)*")

        st.markdown("### 🌊 대운 (10년 주기)")
        cur = dae['current']
        cur_txt = f"{cur['gz']}({cur['sib']}), {cur['age']}세부터" if cur else "아직 대운 시작 전(유년기)"
        cur_label = "현재 대운" if is_today else f"{luck['year_num']}년 대운"
        st.write(f"- **방향**: {'순행' if dae['forward'] else '역행'} · **대운수**: {dae['dae_num']} · **{cur_label}**: {cur_txt}")
        st.write("- **흐름**: " + " · ".join(
            (f"**{x['age']}세 {x['gz']}({x['sib']})**" if x is cur else f"{x['age']}세 {x['gz']}({x['sib']})")
            for x in dae['seq']))

        st.markdown(f"### 📅 {pd_}·{pm}·{py_} (간지) — 기준일 {ref}")
        st.write(f"- **{pd_} 일진**: {luck['day']['han']} (십성 {luck['day']['gan_sib']})")
        st.write(f"- **{pm} 월건**: {luck['month']['han']} (십성 {luck['month']['gan_sib']})")
        st.write(f"- **{py_} 세운**: {luck['year']['han']} (십성 {luck['year']['gan_sib']}, {luck['year_num']}년)")

        st.markdown("### 🍀 좋은 날 (간이 택일·참고용)")
        if good:
            for gd in good:
                st.write(f"- **{gd['date']}({gd['wd']})** · {gd['gz']}일 · 길신 {gd['sib']}")
            st.caption("※ 일간 기준 길신일(식신·정재·정관·정인)을 추린 간이 택일입니다. 정통 택일과 다를 수 있습니다.")
        else:
            st.write("향후 45일 내 해당 길일이 없습니다.")

        st.markdown("### 🪙 토정비결 작괘 (간이·오락용)")
        st.write(f"- **{luck['year_num']}년 괘**: {toj['gua']}괘 (上{toj['sang']} 中{toj['jung']} 下{toj['ha']}) · 상괘 {toj['sang_name']}")
        st.write(f"- 세는나이 {toj['age']} · 음력생일 {toj['lunar']} · 올해 {toj['year_gz']}년")
        st.caption("※ 선천수 기반 작괘 공식(상8·중6·하3진)입니다. 정통 조견표·144괘 원문과는 차이가 있을 수 있는 오락용입니다.")

        st.markdown("### 🤖 AI 운세 해석 (성격·오행·직업재물 + 대운 + 오늘·주간·월간·올해 금전/사업 + 토정)")
        if not api_key:
            st.warning("사이드바에 Anthropic API Key를 입력하면 AI 운세 해석이 활성화됩니다.")
        else:
            if st.button("AI 운세 생성", use_container_width=True):
                if not api_key.isascii():
                    st.error("API 키에 한글·공백 등 영문이 아닌 문자가 섞여 있습니다. "
                             "키는 sk-ant- 로 시작하는 영문·숫자입니다. 입력란을 모두 지우고, "
                             "키보드를 영문(한/영)으로 바꾼 뒤 다시 붙여넣어 주세요.")
                else:
                    with st.spinner(f"운세를 해석하는 중입니다... (모델: {model})"):
                        try:
                            st.session_state["ai_result"] = ai_interpretation(
                                s, gender, birth_label, luck, dae, toj, ref, is_today, api_key, model)
                        except Exception as e:
                            st.error(f"AI 호출 중 오류가 발생했습니다: {e}")
            if st.session_state.get("ai_result"):
                st.markdown(st.session_state["ai_result"])

        st.markdown("### 📤 결과 저장·공유 (다른 사람에게 전달)")
        report = build_report(s, birth_label, gender, luck, dae, good, toj,
                              st.session_state.get("ai_result"))
        plain = to_plaintext(report)
        st.download_button("📥 파일로 저장 (.md · 이메일·보관·인쇄용)", data=report,
                           file_name=f"사주운세_{luck['date']}.md",
                           mime="text/markdown", use_container_width=True)
        with st.expander("💬 카톡·문자용 텍스트 복사 (우측 상단 복사 아이콘) — 붙여넣기용"):
            st.code(plain)
        st.caption("※ 카톡·문자는 위 '카톡·문자용 텍스트'를 복사해 붙여넣으면 깔끔합니다. "
                   "이메일·보관·인쇄는 파일 저장(.md)이 적합합니다.")

    st.markdown("---")
    st.caption("※ 만세력은 절기·입춘 경계를 반영합니다. 대운은 양남음녀 기준 순행/역행. 좋은날·토정비결은 간이 버전입니다.")


if __name__ == "__main__":
    main()
