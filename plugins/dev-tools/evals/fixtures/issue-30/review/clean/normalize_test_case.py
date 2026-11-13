from normalize import normalize_name


def test_normalize_name_trims_collapses_and_casefolds():
    assert normalize_name("  SummerField   Zoo ") == "summerfield zoo"
