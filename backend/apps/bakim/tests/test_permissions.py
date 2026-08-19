from types import SimpleNamespace

from rest_framework.permissions import SAFE_METHODS

from apps.bakim.permissions import BakimApiIzni


def _request(method, *, authenticated, active=True, role="USER"):
    user = SimpleNamespace(
        is_authenticated=authenticated,
        is_active=active,
        rol=role,
    )
    return SimpleNamespace(method=method, user=user)


def test_safe_methods_anonymous_kullaniciya_kosulsuz_izin_vermez():
    permission = BakimApiIzni()
    for method in SAFE_METHODS:
        assert (
            permission.has_permission(_request(method, authenticated=False), view=None)
            is False
        )


def test_operasyonel_read_aktif_user_ve_admine_aciktir():
    permission = BakimApiIzni()
    assert permission.has_permission(
        _request("GET", authenticated=True, role="USER"), view=None
    )
    assert permission.has_permission(
        _request("GET", authenticated=True, role="ADMIN"), view=None
    )
    assert not permission.has_permission(
        _request("GET", authenticated=True, active=False), view=None
    )


def test_mutation_yalniz_aktif_admine_aciktir():
    permission = BakimApiIzni()
    assert not permission.has_permission(
        _request("POST", authenticated=True, role="USER"), view=None
    )
    assert permission.has_permission(
        _request("POST", authenticated=True, role="ADMIN"), view=None
    )
