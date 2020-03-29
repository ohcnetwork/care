class EverythingEquals:
    def __eq__(self, other):
        return True


mock_equal = EverythingEquals()


def assert_equal_dicts(d1, d2, ignore_keys=[]):
    def check_equal():
        ignored = set(ignore_keys)
        for k1, v1 in d1.items():
            if k1 not in ignored and (k1 not in d2 or d2[k1] != v1):
                print(k1, v1, d2[k1])
                return False
        for k2, v2 in d2.items():
            if k2 not in ignored and k2 not in d1:
                print(k2, v2)
                return False
        return True

    return check_equal()
