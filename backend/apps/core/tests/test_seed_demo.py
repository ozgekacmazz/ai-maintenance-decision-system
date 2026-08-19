from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management.base import CommandError
from django.test import override_settings

from apps.core.management.commands.seed_demo import Command
from apps.kullanicilar.models import Kullanici
from apps.tahminler.exceptions import ReplayVeriSetiHatasi


def test_demo_replay_uses_public_service_with_bounded_real_items():
    command = Command(stdout=StringIO())
    actor = SimpleNamespace(id=1)
    machine = SimpleNamespace(id=42)
    session = SimpleNamespace(id="real-session")

    with (
        patch(
            "apps.core.management.commands.seed_demo.replay_olustur",
            return_value=session,
        ) as create,
        patch(
            "apps.core.management.commands.seed_demo.replay_butunlugunu_dogrula",
            return_value=250,
        ) as validate,
    ):
        result = command._replay_hazirla(admin_user=actor, machine=machine)

    assert result is session
    create.assert_called_once_with(
        actor=actor,
        trace_id="seed-demo-replay",
        data={
            "makine_id": 42,
            "split": "test",
            "baslangic_ofseti": 0,
            "kayit_sayisi": 250,
            "varsayilan_batch_boyutu": 5,
            "sanal_aralik_saniye": 60,
        },
        idempotent=True,
    )
    validate.assert_called_once_with(session)


def test_small_dataset_reports_real_count_warning():
    output = StringIO()
    command = Command(stdout=output)
    with (
        patch(
            "apps.core.management.commands.seed_demo.replay_olustur",
            return_value=SimpleNamespace(id="small"),
        ),
        patch(
            "apps.core.management.commands.seed_demo.replay_butunlugunu_dogrula",
            return_value=40,
        ),
    ):
        command._replay_hazirla(
            admin_user=SimpleNamespace(id=1), machine=SimpleNamespace(id=2)
        )

    assert "40 gerçek replay öğesi" in output.getvalue()


def test_missing_dataset_fails_without_success_message():
    output = StringIO()
    command = Command(stdout=output)
    with patch(
        "apps.core.management.commands.seed_demo.replay_olustur",
        side_effect=ReplayVeriSetiHatasi(),
    ):
        with pytest.raises(CommandError, match="prepared AI4I"):
            command._replay_hazirla(
                admin_user=SimpleNamespace(id=1), machine=SimpleNamespace(id=2)
            )

    assert "HAZIR durumda oluşturuldu" not in output.getvalue()


def test_demo_credentials_are_required(monkeypatch):
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_USER_PASSWORD", raising=False)
    with override_settings(DEBUG=True), pytest.raises(CommandError):
        Command._env_hesaplarini_dogrula()


def test_weak_demo_password_fails_without_leaking_value(monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "123")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "Guclu!Demo-User-2026")
    with override_settings(DEBUG=True), pytest.raises(CommandError) as exc_info:
        Command._env_hesaplarini_dogrula()
    assert "123" not in str(exc_info.value)


def test_valid_demo_credentials_return_canonical_roles(monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_USERNAME", "sunum-admin")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "Guclu!Demo-Admin-2026")
    monkeypatch.setenv("DEMO_USER_USERNAME", "sunum-user")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "Guclu!Demo-User-2026")
    with override_settings(DEBUG=True):
        specs = Command._env_hesaplarini_dogrula()
    assert [(item[1], item[3]) for item in specs] == [
        ("sunum-admin", Kullanici.Rol.ADMIN),
        ("sunum-user", Kullanici.Rol.USER),
    ]


def test_production_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "Guclu!Demo-Admin-2026")
    monkeypatch.setenv("DEMO_USER_PASSWORD", "Guclu!Demo-User-2026")
    monkeypatch.delenv("ALLOW_DEMO_SEED_IN_PRODUCTION", raising=False)
    with (
        override_settings(DEBUG=False),
        pytest.raises(CommandError, match="açık onayı"),
    ):
        Command._env_hesaplarini_dogrula()
