# -*- coding: utf-8 -*-
"""세 렌즈 판독 엔진 검증. 실행: python test_three_lens.py"""
import datetime

import saju_app as A


def chart(*pillars):
    """'임자' 형식 간지 3~4개(년·월·일·시)로 판정용 원국을 만든다."""
    keys = ['년', '월', '일', '시']
    dg = A.GAN.index(pillars[2][0])
    pp, elem = {}, {e: 0 for e in A.ELEM_ORDER}
    groups = {'비겁': 0, '식상': 0, '재성': 0, '관성': 0, '인성': 0}
    for k, gz in zip(keys, pillars):
        g, z = A.GAN.index(gz[0]), A.ZHI.index(gz[1])
        pp[k] = {'gan': g, 'zhi': z, 'han': gz,
                 'gan_sib': '일간(我身)' if k == '일' else A.ten_god(dg, g),
                 'zhi_sib': A.ten_god(dg, A.ZHI_MAIN_GAN[z])}
        elem[A.GAN_ELEM[g]] += 1
        elem[A.ZHI_ELEM[z]] += 1
        if k != '일':
            groups[A.SIBSEONG_GROUP[pp[k]['gan_sib']]] += 1
        groups[A.SIBSEONG_GROUP[pp[k]['zhi_sib']]] += 1
    return {'pillars': pp, 'elem': elem, 'groups': groups, 'strength': '중화',
            'day_gan': A.GAN[dg], 'day_gan_idx': dg, 'day_elem': A.GAN_ELEM[dg],
            'day_yin': '양', 'month_zhi': pp['월']['zhi'], 'month_gan': pp['월']['gan'],
            'time_known': len(pillars) == 4}


def test_table():
    assert set(A.JOHU_TABLE) == set(A.GAN_HJ)
    for row in A.JOHU_TABLE.values():
        assert len(row) == 12
        assert all(c in A.GAN_HJ for cell in row for c in cell)


def test_table_matches_month_text():
    """본문 월별 첫 문장과 대조한 칸."""
    T = A.JOHU_TABLE
    m = A.JOHU_MONTHS.index
    assert T['丁'][m('未')] == '甲壬庚'     # 專取甲木, 壬水次之, 無庚不妙
    assert T['戊'][m('午')] == '壬甲丙'     # 先看壬水, 次取甲木, 丙火酌用
    assert T['庚'][m('未')] == '丁甲'       # 先用丁火, 次取甲木
    assert T['乙'][m('辰')][:2] == '癸丙'   # 先癸後丙
    assert T['丙'][m('戌')] == '甲壬'       # 先用甲木, 次取壬水


def test_jae_state_classics():
    """적천수 반국의 임철초 예시로 판정 방향을 고정한다."""
    assert A.jae_state(chart('임진', '임자', '갑인', '무진'))[0] == '유기'   # 君賴臣生
    assert A.jae_state(chart('임자', '임인', '갑자', '임신'))[0] == '무기'   # 母慈滅子
    assert A.jae_state(chart('계묘', '갑인', '정묘', '갑진'))[0] == '무기'   # 母慈滅子
    assert A.jae_state(chart('임자', '병자', '갑자', '무자'))[0] == '약'


def test_jaegeukin_branches():
    assert '적용(군뢰신생' in A.jaegeukin_block(chart('임진', '임자', '갑인', '무진'))
    no = A.jaegeukin_block(chart('임자', '임인', '갑자', '임신'))
    assert '미적용(모자멸자' in no and '재성을 용신으로 잡지 않는다' in no
    assert '조건부' in A.jaegeukin_block(chart('임자', '병자', '갑자', '무자'))


def test_gyeokguk():
    assert A.gyeokguk(chart('갑자', '병인', '갑자', '무진'))['key'] == '건록'
    gk = A.gyeokguk(chart('경자', '계축', '갑자', '신미'))   # 축월 신·계 투간
    assert gk['key'] == '정관' and '계' in gk['also']
    none = A.gyeokguk(chart('경자', '계미', '정유', '경자'))  # 미월 투간·회지 없음
    assert none['key'] == '식신' and '토로 논해' in none['basis']
    hoe = A.gyeokguk(chart('신해', '계미', '정묘', '경자'))   # 미월 해묘미 회국
    assert hoe['key'] == '편인' and '회지' in hoe['basis']
    half = A.gyeokguk(chart('경자', '계미', '정묘', '경자'))  # 반회는 격을 바꾸지 않는다
    assert half['key'] == '식신' and half['half'] == ['해묘미']


def test_relations():
    assert A.branch_relations('묘', '오') == ['파']
    assert '충' in A.branch_relations('축', '미')
    assert A.branch_relations('미', '미') == ['복음']
    assert A.branch_relations('진', '진') == ['자형']
    assert A.completed_guk(['묘', '미', '진'], ['해']) == ['해묘미 목국(삼합)']
    assert any('인묘진' in x for x in A.completed_guk(['묘', '미', '진'], ['인']))


def test_roles_and_verdict():
    s = chart('임자', '병자', '갑자', '무자')          # 인성 과다·재성 약
    assert A.element_roles(s)[0] == 'jae'
    assert A.element_roles(chart('임자', '임인', '갑자', '임신'))[0] == 'mother'
    assert A.luck_verdict(s, '무진', '대운')['verdict'] == '유리'
    assert A.luck_verdict(s, '임자', '대운')['verdict'] == '주의'
    assert A.day_conflicts_roles(s, '임자') and not A.day_conflicts_roles(s, '무진')


def test_detail_reading_sections():
    s = A.compute_saju(1978, 8, 20, 9)
    today = datetime.date(2026, 11, 19)
    text = A.detail_reading(s, A.major_luck(s, 1978, 8, 20, False, False, '남성', today=today), A.luck_context(s, today=today))
    for key in ('### 총론', '### 대운 풀이', '### 연운 풀이', '2030년'):
        assert key in text, key


def test_real_charts_build_prompt():
    today = datetime.date(2026, 11, 19)
    for y, m, d, h, sex in [(1978, 8, 20, 9, '남성'), (1990, 3, 15, 14, '여성'), (1990, 3, 15, None, '여성')]:
        s = A.compute_saju(y, m, d, h)
        luck = A.luck_context(s, today=today)
        dae = A.major_luck(s, y, m, d, False, False, sex, today=today)
        toj = A.tojeong_gua(y, m, d, False, False, today=today)
        text = A.build_prompt(s, sex, 'label', luck, dae, toj, today.isoformat(), True)
        for key in ('[자평진전', '[궁통보감', '[적천수', '세 렌즈 교차 판독', '과거 대운 검증 질문'):
            assert key in text, key


if __name__ == '__main__':
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            try:
                fn()
                print('PASS', name)
            except Exception as e:
                fails += 1
                print('FAIL', name, repr(e))
    raise SystemExit(1 if fails else 0)
