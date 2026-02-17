import json
from pathlib import Path

import pytest


EXPECTED = {
    "1": "c",
    "2": "b",
    "3": "c",
    "4": "b",
    "5": "c",
    "6": "a",
    "7": "b",
    "8": "a",
    "9": "c",
    "10": "a",
    "11": "c",
    "12": "a",
    "13": "a",
    "14": "a",
    "15": "b",
    "16": "a",
    "17": "b",
    "18": "d",
    "19": "c",
    "20": "b",
    "21": "d",
    "22": "b",
    "23": "a",
    "24": "c",
    "25": "d",
    "26": "c",
    "27": "d",
    "28": "d",
    "29": "b",
    "30": "a",
    "31": "b",
    "32": "c",
    "33": "c",
    "34": "d",
    "35": "b",
    "36": "a",
    "37": "d",
    "38": "c",
    "39": "c",
    "40": "d",
    "41": "c",
    "42": "c",
    "43": "c",
    "44": "a",
    "45": "d",
    "46": "b",
    "47": "c",
    "48": "c",
    "49": "c",
    "50": "d",
    "51": "b",
    "52": "a",
    "53": "a",
    "54": "a",
    "55": "c",
    "56": "d",
    "57": "a",
    "58": "a",
    "59": "a",
    "60": "a",
    "61": "d",
    "62": "d",
    "63": "a",
    "64": "a",
    "65": "d",
    "66": "b",
    "67": "d",
    "68": "b",
    "69": "c",
    "70": "b",
    "71": "c",
    "72": "a",
    "73": "c",
    "74": "a",
    "75": "c",
    "76": "d",
    "77": "c",
    "78": "b",
    "79": "c",
    "80": "b",
    "81": "d",
    "82": "d",
    "83": "d",
    "84": "b",
    "85": "c",
    "86": "b",
    "87": "d",
    "88": "a",
    "89": "b",
    "90": "c",
    "91": "c",
    "92": "c",
    "93": "c",
    "94": "b",
    "95": "a",
    "96": "b",
    "97": "c",
    "98": "a",
}


@pytest.fixture(scope="module")
def answers():
    f = Path("/app/answers.json")
    assert f.exists(), "answers.json not found"
    return json.loads(f.read_text())


def test_question_1(answers):
    got = answers.get("1", "").strip().lower()
    assert got == "c", f"Q1: expected 'c', got '{got}'"


def test_question_2(answers):
    got = answers.get("2", "").strip().lower()
    assert got == "b", f"Q2: expected 'b', got '{got}'"


def test_question_3(answers):
    got = answers.get("3", "").strip().lower()
    assert got == "c", f"Q3: expected 'c', got '{got}'"


def test_question_4(answers):
    got = answers.get("4", "").strip().lower()
    assert got == "b", f"Q4: expected 'b', got '{got}'"


def test_question_5(answers):
    got = answers.get("5", "").strip().lower()
    assert got == "c", f"Q5: expected 'c', got '{got}'"


def test_question_6(answers):
    got = answers.get("6", "").strip().lower()
    assert got == "a", f"Q6: expected 'a', got '{got}'"


def test_question_7(answers):
    got = answers.get("7", "").strip().lower()
    assert got == "b", f"Q7: expected 'b', got '{got}'"


def test_question_8(answers):
    got = answers.get("8", "").strip().lower()
    assert got == "a", f"Q8: expected 'a', got '{got}'"


def test_question_9(answers):
    got = answers.get("9", "").strip().lower()
    assert got == "c", f"Q9: expected 'c', got '{got}'"


def test_question_10(answers):
    got = answers.get("10", "").strip().lower()
    assert got == "a", f"Q10: expected 'a', got '{got}'"


def test_question_11(answers):
    got = answers.get("11", "").strip().lower()
    assert got == "c", f"Q11: expected 'c', got '{got}'"


def test_question_12(answers):
    got = answers.get("12", "").strip().lower()
    assert got == "a", f"Q12: expected 'a', got '{got}'"


def test_question_13(answers):
    got = answers.get("13", "").strip().lower()
    assert got == "a", f"Q13: expected 'a', got '{got}'"


def test_question_14(answers):
    got = answers.get("14", "").strip().lower()
    assert got == "a", f"Q14: expected 'a', got '{got}'"


def test_question_15(answers):
    got = answers.get("15", "").strip().lower()
    assert got == "b", f"Q15: expected 'b', got '{got}'"


def test_question_16(answers):
    got = answers.get("16", "").strip().lower()
    assert got == "a", f"Q16: expected 'a', got '{got}'"


def test_question_17(answers):
    got = answers.get("17", "").strip().lower()
    assert got == "b", f"Q17: expected 'b', got '{got}'"


def test_question_18(answers):
    got = answers.get("18", "").strip().lower()
    assert got == "d", f"Q18: expected 'd', got '{got}'"


def test_question_19(answers):
    got = answers.get("19", "").strip().lower()
    assert got == "c", f"Q19: expected 'c', got '{got}'"


def test_question_20(answers):
    got = answers.get("20", "").strip().lower()
    assert got == "b", f"Q20: expected 'b', got '{got}'"


def test_question_21(answers):
    got = answers.get("21", "").strip().lower()
    assert got == "d", f"Q21: expected 'd', got '{got}'"


def test_question_22(answers):
    got = answers.get("22", "").strip().lower()
    assert got == "b", f"Q22: expected 'b', got '{got}'"


def test_question_23(answers):
    got = answers.get("23", "").strip().lower()
    assert got == "a", f"Q23: expected 'a', got '{got}'"


def test_question_24(answers):
    got = answers.get("24", "").strip().lower()
    assert got == "c", f"Q24: expected 'c', got '{got}'"


def test_question_25(answers):
    got = answers.get("25", "").strip().lower()
    assert got == "d", f"Q25: expected 'd', got '{got}'"


def test_question_26(answers):
    got = answers.get("26", "").strip().lower()
    assert got == "c", f"Q26: expected 'c', got '{got}'"


def test_question_27(answers):
    got = answers.get("27", "").strip().lower()
    assert got == "d", f"Q27: expected 'd', got '{got}'"


def test_question_28(answers):
    got = answers.get("28", "").strip().lower()
    assert got == "d", f"Q28: expected 'd', got '{got}'"


def test_question_29(answers):
    got = answers.get("29", "").strip().lower()
    assert got == "b", f"Q29: expected 'b', got '{got}'"


def test_question_30(answers):
    got = answers.get("30", "").strip().lower()
    assert got == "a", f"Q30: expected 'a', got '{got}'"


def test_question_31(answers):
    got = answers.get("31", "").strip().lower()
    assert got == "b", f"Q31: expected 'b', got '{got}'"


def test_question_32(answers):
    got = answers.get("32", "").strip().lower()
    assert got == "c", f"Q32: expected 'c', got '{got}'"


def test_question_33(answers):
    got = answers.get("33", "").strip().lower()
    assert got == "c", f"Q33: expected 'c', got '{got}'"


def test_question_34(answers):
    got = answers.get("34", "").strip().lower()
    assert got == "d", f"Q34: expected 'd', got '{got}'"


def test_question_35(answers):
    got = answers.get("35", "").strip().lower()
    assert got == "b", f"Q35: expected 'b', got '{got}'"


def test_question_36(answers):
    got = answers.get("36", "").strip().lower()
    assert got == "a", f"Q36: expected 'a', got '{got}'"


def test_question_37(answers):
    got = answers.get("37", "").strip().lower()
    assert got == "d", f"Q37: expected 'd', got '{got}'"


def test_question_38(answers):
    got = answers.get("38", "").strip().lower()
    assert got == "c", f"Q38: expected 'c', got '{got}'"


def test_question_39(answers):
    got = answers.get("39", "").strip().lower()
    assert got == "c", f"Q39: expected 'c', got '{got}'"


def test_question_40(answers):
    got = answers.get("40", "").strip().lower()
    assert got == "d", f"Q40: expected 'd', got '{got}'"


def test_question_41(answers):
    got = answers.get("41", "").strip().lower()
    assert got == "c", f"Q41: expected 'c', got '{got}'"


def test_question_42(answers):
    got = answers.get("42", "").strip().lower()
    assert got == "c", f"Q42: expected 'c', got '{got}'"


def test_question_43(answers):
    got = answers.get("43", "").strip().lower()
    assert got == "c", f"Q43: expected 'c', got '{got}'"


def test_question_44(answers):
    got = answers.get("44", "").strip().lower()
    assert got == "a", f"Q44: expected 'a', got '{got}'"


def test_question_45(answers):
    got = answers.get("45", "").strip().lower()
    assert got == "d", f"Q45: expected 'd', got '{got}'"


def test_question_46(answers):
    got = answers.get("46", "").strip().lower()
    assert got == "b", f"Q46: expected 'b', got '{got}'"


def test_question_47(answers):
    got = answers.get("47", "").strip().lower()
    assert got == "c", f"Q47: expected 'c', got '{got}'"


def test_question_48(answers):
    got = answers.get("48", "").strip().lower()
    assert got == "c", f"Q48: expected 'c', got '{got}'"


def test_question_49(answers):
    got = answers.get("49", "").strip().lower()
    assert got == "c", f"Q49: expected 'c', got '{got}'"


def test_question_50(answers):
    got = answers.get("50", "").strip().lower()
    assert got == "d", f"Q50: expected 'd', got '{got}'"


def test_question_51(answers):
    got = answers.get("51", "").strip().lower()
    assert got == "b", f"Q51: expected 'b', got '{got}'"


def test_question_52(answers):
    got = answers.get("52", "").strip().lower()
    assert got == "a", f"Q52: expected 'a', got '{got}'"


def test_question_53(answers):
    got = answers.get("53", "").strip().lower()
    assert got == "a", f"Q53: expected 'a', got '{got}'"


def test_question_54(answers):
    got = answers.get("54", "").strip().lower()
    assert got == "a", f"Q54: expected 'a', got '{got}'"


def test_question_55(answers):
    got = answers.get("55", "").strip().lower()
    assert got == "c", f"Q55: expected 'c', got '{got}'"


def test_question_56(answers):
    got = answers.get("56", "").strip().lower()
    assert got == "d", f"Q56: expected 'd', got '{got}'"


def test_question_57(answers):
    got = answers.get("57", "").strip().lower()
    assert got == "a", f"Q57: expected 'a', got '{got}'"


def test_question_58(answers):
    got = answers.get("58", "").strip().lower()
    assert got == "a", f"Q58: expected 'a', got '{got}'"


def test_question_59(answers):
    got = answers.get("59", "").strip().lower()
    assert got == "a", f"Q59: expected 'a', got '{got}'"


def test_question_60(answers):
    got = answers.get("60", "").strip().lower()
    assert got == "a", f"Q60: expected 'a', got '{got}'"


def test_question_61(answers):
    got = answers.get("61", "").strip().lower()
    assert got == "d", f"Q61: expected 'd', got '{got}'"


def test_question_62(answers):
    got = answers.get("62", "").strip().lower()
    assert got == "d", f"Q62: expected 'd', got '{got}'"


def test_question_63(answers):
    got = answers.get("63", "").strip().lower()
    assert got == "a", f"Q63: expected 'a', got '{got}'"


def test_question_64(answers):
    got = answers.get("64", "").strip().lower()
    assert got == "a", f"Q64: expected 'a', got '{got}'"


def test_question_65(answers):
    got = answers.get("65", "").strip().lower()
    assert got == "d", f"Q65: expected 'd', got '{got}'"


def test_question_66(answers):
    got = answers.get("66", "").strip().lower()
    assert got == "b", f"Q66: expected 'b', got '{got}'"


def test_question_67(answers):
    got = answers.get("67", "").strip().lower()
    assert got == "d", f"Q67: expected 'd', got '{got}'"


def test_question_68(answers):
    got = answers.get("68", "").strip().lower()
    assert got == "b", f"Q68: expected 'b', got '{got}'"


def test_question_69(answers):
    got = answers.get("69", "").strip().lower()
    assert got == "c", f"Q69: expected 'c', got '{got}'"


def test_question_70(answers):
    got = answers.get("70", "").strip().lower()
    assert got == "b", f"Q70: expected 'b', got '{got}'"


def test_question_71(answers):
    got = answers.get("71", "").strip().lower()
    assert got == "c", f"Q71: expected 'c', got '{got}'"


def test_question_72(answers):
    got = answers.get("72", "").strip().lower()
    assert got == "a", f"Q72: expected 'a', got '{got}'"


def test_question_73(answers):
    got = answers.get("73", "").strip().lower()
    assert got == "c", f"Q73: expected 'c', got '{got}'"


def test_question_74(answers):
    got = answers.get("74", "").strip().lower()
    assert got == "a", f"Q74: expected 'a', got '{got}'"


def test_question_75(answers):
    got = answers.get("75", "").strip().lower()
    assert got == "c", f"Q75: expected 'c', got '{got}'"


def test_question_76(answers):
    got = answers.get("76", "").strip().lower()
    assert got == "d", f"Q76: expected 'd', got '{got}'"


def test_question_77(answers):
    got = answers.get("77", "").strip().lower()
    assert got == "c", f"Q77: expected 'c', got '{got}'"


def test_question_78(answers):
    got = answers.get("78", "").strip().lower()
    assert got == "b", f"Q78: expected 'b', got '{got}'"


def test_question_79(answers):
    got = answers.get("79", "").strip().lower()
    assert got == "c", f"Q79: expected 'c', got '{got}'"


def test_question_80(answers):
    got = answers.get("80", "").strip().lower()
    assert got == "b", f"Q80: expected 'b', got '{got}'"


def test_question_81(answers):
    got = answers.get("81", "").strip().lower()
    assert got == "d", f"Q81: expected 'd', got '{got}'"


def test_question_82(answers):
    got = answers.get("82", "").strip().lower()
    assert got == "d", f"Q82: expected 'd', got '{got}'"


def test_question_83(answers):
    got = answers.get("83", "").strip().lower()
    assert got == "d", f"Q83: expected 'd', got '{got}'"


def test_question_84(answers):
    got = answers.get("84", "").strip().lower()
    assert got == "b", f"Q84: expected 'b', got '{got}'"


def test_question_85(answers):
    got = answers.get("85", "").strip().lower()
    assert got == "c", f"Q85: expected 'c', got '{got}'"


def test_question_86(answers):
    got = answers.get("86", "").strip().lower()
    assert got == "b", f"Q86: expected 'b', got '{got}'"


def test_question_87(answers):
    got = answers.get("87", "").strip().lower()
    assert got == "d", f"Q87: expected 'd', got '{got}'"


def test_question_88(answers):
    got = answers.get("88", "").strip().lower()
    assert got == "a", f"Q88: expected 'a', got '{got}'"


def test_question_89(answers):
    got = answers.get("89", "").strip().lower()
    assert got == "b", f"Q89: expected 'b', got '{got}'"


def test_question_90(answers):
    got = answers.get("90", "").strip().lower()
    assert got == "c", f"Q90: expected 'c', got '{got}'"


def test_question_91(answers):
    got = answers.get("91", "").strip().lower()
    assert got == "c", f"Q91: expected 'c', got '{got}'"


def test_question_92(answers):
    got = answers.get("92", "").strip().lower()
    assert got == "c", f"Q92: expected 'c', got '{got}'"


def test_question_93(answers):
    got = answers.get("93", "").strip().lower()
    assert got == "c", f"Q93: expected 'c', got '{got}'"


def test_question_94(answers):
    got = answers.get("94", "").strip().lower()
    assert got == "b", f"Q94: expected 'b', got '{got}'"


def test_question_95(answers):
    got = answers.get("95", "").strip().lower()
    assert got == "a", f"Q95: expected 'a', got '{got}'"


def test_question_96(answers):
    got = answers.get("96", "").strip().lower()
    assert got == "b", f"Q96: expected 'b', got '{got}'"


def test_question_97(answers):
    got = answers.get("97", "").strip().lower()
    assert got == "c", f"Q97: expected 'c', got '{got}'"


def test_question_98(answers):
    got = answers.get("98", "").strip().lower()
    assert got == "a", f"Q98: expected 'a', got '{got}'"
