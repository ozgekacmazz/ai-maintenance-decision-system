"""Deterministik, veri tabanından bağımsız OpenAPI 3.0 sözleşmesi."""

from copy import deepcopy

from drf_spectacular.generators import SchemaGenerator

ERROR_RESPONSES = {
    str(code): {"$ref": "#/components/responses/StandartHata"}
    for code in (400, 401, 403, 404, 409, 503)
}


def _ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def _response(name, status=200):
    return {
        str(status): {
            "description": "Başarılı",
            "content": {"application/json": {"schema": _ref(name)}},
        },
        **deepcopy(ERROR_RESPONSES),
    }


def _operation(
    operation_id,
    tag,
    *,
    request=None,
    response="Nesne",
    status=200,
    parameters=None,
    public=False,
):
    value = {
        "operationId": operation_id,
        "tags": [tag],
        "responses": _response(response, status),
        "security": [] if public else [{"jwtAuth": []}],
    }
    if request:
        value["requestBody"] = {
            "required": True,
            "content": {"application/json": {"schema": _ref(request)}},
        }
    if parameters:
        value["parameters"] = parameters
    return value


def _query(name, schema, description=None):
    result = {"name": name, "in": "query", "required": False, "schema": schema}
    if description:
        result["description"] = description
    return result


def _path(name, schema_type="string", fmt=None):
    schema = {"type": schema_type}
    if fmt:
        schema["format"] = fmt
    return {"name": name, "in": "path", "required": True, "schema": schema}


PAGINATION = [
    _query("sayfa", {"type": "integer", "minimum": 1}),
    _query("sayfa_boyutu", {"type": "integer", "minimum": 1, "maximum": 100}),
]
UUID_PK = [_path("pk", fmt="uuid")]
INT_PK = [_path("pk", "integer")]
PRIORITY = {"type": "integer", "minimum": 1, "maximum": 5}


def build_openapi_schema():
    prediction_filters = PAGINATION + [
        _query("makine_id", {"type": "integer", "minimum": 1}),
        _query("kaynak", {"type": "string", "enum": ["MANUEL", "REPLAY"]}),
        _query("genel_oncelik", PRIORITY),
        _query("baslangic", {"type": "string", "format": "date"}),
        _query("bitis", {"type": "string", "format": "date"}),
        _query(
            "sirala",
            {
                "type": "string",
                "enum": [
                    "olcum_zamani",
                    "-olcum_zamani",
                    "risk_orani",
                    "-risk_orani",
                    "genel_oncelik",
                    "-genel_oncelik",
                ],
            },
        ),
    ]
    work_order_filters = PAGINATION + [
        _query(
            "durum",
            {
                "type": "string",
                "enum": [
                    "ACIK",
                    "ATANDI",
                    "DEVAM_EDIYOR",
                    "BEKLEMEDE",
                    "TAMAMLANDI",
                    "IPTAL_EDILDI",
                ],
            },
        ),
        _query("genel_oncelik", PRIORITY),
        _query(
            "sirala",
            {
                "type": "string",
                "enum": [
                    "etkin_genel_oncelik",
                    "-etkin_genel_oncelik",
                    "hedef_mudahale_zamani",
                    "-hedef_mudahale_zamani",
                    "olusturulma_zamani",
                    "-olusturulma_zamani",
                ],
            },
        ),
    ]
    log_filters = PAGINATION + [
        _query(
            "karar_durumu",
            {
                "type": "string",
                "enum": ["BEKLIYOR", "ONAYLANDI", "REDDEDILDI", "TUTARSIZ"],
            },
        ),
        _query("kaynak", {"type": "string", "enum": ["MANUEL", "REPLAY"]}),
        _query("genel_oncelik", PRIORITY),
        _query("baslangic", {"type": "string", "format": "date"}),
        _query("bitis", {"type": "string", "format": "date"}),
        _query(
            "sirala",
            {
                "type": "string",
                "enum": [
                    "karar_zamani",
                    "-karar_zamani",
                    "genel_oncelik",
                    "-genel_oncelik",
                ],
            },
        ),
    ]
    paths = {
        "/api/saglik/": {
            "get": _operation("saglik_getir", "Sistem", response="Saglik", public=True)
        },
        "/api/auth/csrf/": {
            "get": _operation("csrf_getir", "Kimlik", response="Csrf", public=True)
        },
        "/api/auth/login/": {
            "post": _operation(
                "oturum_ac",
                "Kimlik",
                request="LoginRequest",
                response="LoginResponse",
                public=True,
            )
        },
        "/api/auth/refresh/": {
            "post": _operation(
                "token_yenile", "Kimlik", response="TokenResponse", public=True
            )
        },
        "/api/auth/logout/": {
            "post": _operation("oturum_kapat", "Kimlik", response="Mesaj")
        },
        "/api/auth/me/": {
            "get": _operation("aktif_kullanici_getir", "Kimlik", response="Kullanici")
        },
        "/api/auth/kullanicilar/": {
            "get": _operation(
                "kullanicilari_listele",
                "Kullanıcı Yönetimi",
                response="KullaniciListesi",
            ),
            "post": _operation(
                "kullanici_olustur",
                "Kullanıcı Yönetimi",
                request="KullaniciOlusturRequest",
                response="Kullanici",
                status=201,
            ),
        },
        "/api/auth/kullanicilar/{pk}/": {
            "patch": _operation(
                "kullanici_guncelle",
                "Kullanıcı Yönetimi",
                request="KullaniciGuncelleRequest",
                response="Kullanici",
                parameters=INT_PK,
            )
        },
        "/api/auth/kullanicilar/{pk}/sifre-sifirla/": {
            "post": _operation(
                "kullanici_parola_sifirla",
                "Kullanıcı Yönetimi",
                request="ParolaSifirlaRequest",
                response="Mesaj",
                parameters=INT_PK,
            )
        },
        "/api/makine-secenekleri/": {
            "get": _operation(
                "makine_seceneklerini_listele",
                "Bakım Yönetimi",
                response="SayfaliListe",
                parameters=PAGINATION,
            )
        },
        "/api/makineler/": {
            "get": _operation(
                "makineleri_listele",
                "Bakım Yönetimi",
                response="SayfaliListe",
                parameters=PAGINATION,
            ),
            "post": _operation(
                "makine_olustur",
                "Bakım Yönetimi",
                request="Nesne",
                response="Nesne",
                status=201,
            ),
        },
        "/api/parcalar/": {
            "get": _operation(
                "parcalari_listele",
                "Bakım Yönetimi",
                response="SayfaliListe",
                parameters=PAGINATION,
            ),
            "post": _operation(
                "parca_olustur",
                "Bakım Yönetimi",
                request="Nesne",
                response="Nesne",
                status=201,
            ),
        },
        "/api/stoklar/": {
            "get": _operation(
                "stoklari_listele",
                "Bakım Yönetimi",
                response="SayfaliListe",
                parameters=PAGINATION,
            ),
            "post": _operation(
                "stok_olustur",
                "Bakım Yönetimi",
                request="Nesne",
                response="Nesne",
                status=201,
            ),
        },
        "/api/ariza-parca-kurallari/": {
            "get": _operation(
                "kurallari_listele",
                "Bakım Yönetimi",
                response="SayfaliListe",
                parameters=PAGINATION,
            ),
            "post": _operation(
                "kural_olustur",
                "Bakım Yönetimi",
                request="Nesne",
                response="Nesne",
                status=201,
            ),
        },
        "/api/tahminler/risk/": {
            "post": _operation(
                "hizli_analiz",
                "Tahmin",
                request="SensorRequest",
                response="TahminResponse",
            )
        },
        "/api/tahminler/input-domain/": {
            "get": _operation("input_domain_getir", "Tahmin", response="InputDomain")
        },
        "/api/tahminler/kayitlar/": {
            "get": _operation(
                "tahminleri_listele",
                "Tahmin",
                response="SayfaliListe",
                parameters=prediction_filters,
            ),
            "post": _operation(
                "tahmin_olustur",
                "Tahmin",
                request="TahminKaydiRequest",
                response="TahminDetay",
                status=201,
            ),
        },
        "/api/tahminler/kayitlar/{pk}/": {
            "get": _operation(
                "tahmin_detayi_getir",
                "Tahmin",
                response="TahminDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/kayitlar/{pk}/reddet/": {
            "post": _operation(
                "tahmin_reddet",
                "Tahmin",
                request="TahminReddetRequest",
                response="TahminDetay",
                status=201,
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/loglari/": {
            "get": _operation(
                "tahmin_loglarini_listele",
                "Admin Log",
                response="SayfaliListe",
                parameters=log_filters,
            )
        },
        "/api/bakim/is-emirleri/": {
            "get": _operation(
                "is_emirlerini_listele",
                "İş Emri",
                response="SayfaliListe",
                parameters=work_order_filters,
            ),
            "post": _operation(
                "is_emri_olustur",
                "İş Emri",
                request="IsEmriOlusturRequest",
                response="IsEmri",
                status=201,
            ),
        },
        "/api/bakim/is-emirleri/{pk}/": {
            "get": _operation(
                "is_emri_detayi_getir", "İş Emri", response="IsEmri", parameters=UUID_PK
            )
        },
        "/api/bakim/is-emirleri/{pk}/ata/": {
            "post": _operation(
                "is_emri_ata",
                "İş Emri",
                request="AtamaRequest",
                response="IsEmri",
                parameters=UUID_PK,
            )
        },
        "/api/bakim/is-emirleri/{pk}/durum-gecisi/": {
            "post": _operation(
                "is_emri_durum_gecisi",
                "İş Emri",
                request="DurumGecisiRequest",
                response="IsEmri",
                parameters=UUID_PK,
            )
        },
        "/api/bakim/is-emirleri/{pk}/oncelik-override/": {
            "post": _operation(
                "is_emri_oncelik_override",
                "İş Emri",
                request="OncelikOverrideRequest",
                response="IsEmri",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/": {
            "get": _operation(
                "replay_oturumlarini_listele",
                "Replay",
                response="SayfaliListe",
                parameters=PAGINATION,
            ),
            "post": _operation(
                "replay_oturumu_olustur",
                "Replay",
                request="ReplayOlusturRequest",
                response="ReplayDetay",
                status=201,
            ),
        },
        "/api/tahminler/replay-oturumlari/{pk}/": {
            "get": _operation(
                "replay_detayi_getir",
                "Replay",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/ogeler/": {
            "get": _operation(
                "replay_ogelerini_listele",
                "Replay",
                response="SayfaliListe",
                parameters=UUID_PK + PAGINATION,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/baslat/": {
            "post": _operation(
                "replay_baslat",
                "Replay",
                request="VersionRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/adim/": {
            "post": _operation(
                "replay_adim",
                "Replay",
                request="ReplayAdimRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/duraklat/": {
            "post": _operation(
                "replay_duraklat",
                "Replay",
                request="VersionRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/devam-et/": {
            "post": _operation(
                "replay_devam_et",
                "Replay",
                request="VersionRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/iptal/": {
            "post": _operation(
                "replay_iptal",
                "Replay",
                request="VersionRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
        "/api/tahminler/replay-oturumlari/{pk}/basarisizlari-yeniden-dene/": {
            "post": _operation(
                "replay_basarisizlari_yeniden_dene",
                "Replay",
                request="VersionRequest",
                response="ReplayDetay",
                parameters=UUID_PK,
            )
        },
    }
    return {
        "openapi": "3.0.3",
        "info": {"title": "Bakım Karar Sistemi API", "version": "21.0.0"},
        "paths": paths,
        "components": _components(),
    }


def _components():
    string = {"type": "string"}
    nullable_string = {"type": "string", "nullable": True}
    sensor_properties = {
        "urun_tipi": {"type": "string", "enum": ["L", "M", "H"]},
        "hava_sicakligi_k": {
            "type": "number",
            "format": "double",
            "description": "Kelvin; UI Celsius değerini Kelvin'e dönüştürür.",
        },
        "proses_sicakligi_k": {
            "type": "number",
            "format": "double",
            "description": "Kelvin; UI Celsius değerini Kelvin'e dönüştürür.",
        },
        "donus_hizi_rpm": {"type": "number"},
        "tork_nm": {"type": "number"},
        "takim_asinmasi_dk": {"type": "number"},
    }
    schemas = {
        "Nesne": {"type": "object", "additionalProperties": True},
        "Mesaj": {
            "type": "object",
            "properties": {"mesaj": string},
            "required": ["mesaj"],
        },
        "AlanHatalari": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": string},
        },
        "StandartHata": {
            "type": "object",
            "properties": {
                "hata": {
                    "type": "object",
                    "properties": {
                        "kod": string,
                        "mesaj": string,
                        "alanlar": _ref("AlanHatalari"),
                        "trace_id": nullable_string,
                    },
                    "required": ["kod", "mesaj", "alanlar", "trace_id"],
                }
            },
            "required": ["hata"],
        },
        "Saglik": {
            "type": "object",
            "properties": {"durum": string, "veritabani": string},
        },
        "Csrf": {"type": "object", "properties": {"csrf_token": string}},
        "LoginRequest": {
            "type": "object",
            "properties": {
                "username": string,
                "password": {"type": "string", "format": "password", "writeOnly": True},
            },
            "required": ["username", "password"],
        },
        "TokenResponse": {
            "type": "object",
            "properties": {"access": {"type": "string", "writeOnly": True}},
        },
        "LoginResponse": {
            "type": "object",
            "properties": {
                "access": {"type": "string", "writeOnly": True},
                "kullanici": _ref("Kullanici"),
            },
        },
        "Kullanici": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "username": string,
                "email": string,
                "rol": {"type": "string", "enum": ["ADMIN", "USER"]},
                "is_active": {"type": "boolean"},
            },
        },
        "KullaniciListesi": {"type": "array", "items": _ref("Kullanici")},
        "KullaniciOlusturRequest": {
            "allOf": [
                _ref("Kullanici"),
                {
                    "type": "object",
                    "properties": {
                        "password": {
                            "type": "string",
                            "format": "password",
                            "writeOnly": True,
                        }
                    },
                    "required": ["username", "password", "rol"],
                },
            ]
        },
        "KullaniciGuncelleRequest": {
            "type": "object",
            "properties": {
                "email": string,
                "rol": {"type": "string", "enum": ["ADMIN", "USER"]},
                "is_active": {"type": "boolean"},
            },
        },
        "ParolaSifirlaRequest": {
            "type": "object",
            "properties": {
                "yeni_sifre": {
                    "type": "string",
                    "format": "password",
                    "writeOnly": True,
                }
            },
            "required": ["yeni_sifre"],
        },
        "SayfaliListe": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "next": nullable_string,
                "previous": nullable_string,
                "results": {"type": "array", "items": _ref("Nesne")},
            },
            "required": ["count", "next", "previous", "results"],
        },
        "SensorRequest": {
            "type": "object",
            "properties": sensor_properties,
            "required": list(sensor_properties),
        },
        "TahminKaydiRequest": {
            "allOf": [
                _ref("SensorRequest"),
                {
                    "type": "object",
                    "properties": {
                        "makine_id": {"type": "integer"},
                        "idempotency_key": string,
                    },
                    "required": ["makine_id", "idempotency_key"],
                },
            ]
        },
        "TahminResponse": {
            "type": "object",
            "properties": {
                "risk_orani": {"type": "number"},
                "risk_uyarisi": {"type": "boolean"},
                "genel_oncelik": PRIORITY,
            },
        },
        "TahminDetay": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "bakim_karari": _ref("Nesne"),
                "red_bilgisi": {"allOf": [_ref("Nesne")], "nullable": True},
                "is_emri_bilgisi": {"allOf": [_ref("Nesne")], "nullable": True},
            },
        },
        "TahminReddetRequest": {
            "type": "object",
            "properties": {"red_nedeni": {"type": "string", "maxLength": 500}},
        },
        "InputDomain": {
            "type": "object",
            "properties": {
                "schema_version": string,
                "contract_version": string,
                "features": _ref("Nesne"),
            },
        },
        "IsEmriOlusturRequest": {
            "type": "object",
            "properties": {
                "tahmin_kaydi_id": {"type": "string", "format": "uuid"},
                "idempotency_key": string,
                "baslik": string,
                "aciklama": string,
            },
            "required": ["tahmin_kaydi_id", "idempotency_key", "baslik", "aciklama"],
        },
        "IsEmri": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "durum": string,
                "kaynak_genel_oncelik": {**PRIORITY, "nullable": True},
                "etkin_genel_oncelik": {**PRIORITY, "nullable": True},
                "hedef_mudahale_zamani": {"type": "string", "format": "date-time"},
                "olaylar": {"type": "array", "items": _ref("Nesne")},
            },
        },
        "AtamaRequest": {
            "type": "object",
            "properties": {
                "beklenen_version": {"type": "integer", "minimum": 1},
                "atanan_kullanici_id": {"type": "integer"},
            },
            "required": ["beklenen_version", "atanan_kullanici_id"],
        },
        "DurumGecisiRequest": {
            "type": "object",
            "properties": {
                "beklenen_version": {"type": "integer", "minimum": 1},
                "hedef_durum": string,
                "neden": string,
            },
            "required": ["beklenen_version", "hedef_durum"],
        },
        "OncelikOverrideRequest": {
            "type": "object",
            "properties": {
                "beklenen_version": {"type": "integer", "minimum": 1},
                "genel_oncelik": PRIORITY,
                "etkin_oncelik_seviyesi": {
                    "type": "string",
                    "enum": ["DUSUK", "ORTA", "YUKSEK", "KRITIK"],
                },
                "override_nedeni": string,
            },
            "required": ["beklenen_version", "override_nedeni"],
            "description": "Canonical iş emrinde genel_oncelik, legacy iş emrinde etkin_oncelik_seviyesi kullanılır; ikisi birlikte gönderilmez.",
        },
        "ReplayOlusturRequest": {
            "type": "object",
            "properties": {
                "makine_id": {"type": "integer"},
                "split": {"type": "string", "enum": ["TEST"]},
                "baslangic_ofseti": {"type": "integer", "minimum": 0},
                "toplam_oge": {"type": "integer", "minimum": 1, "maximum": 1000},
                "varsayilan_batch_boyutu": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 25,
                },
            },
            "required": [
                "makine_id",
                "split",
                "baslangic_ofseti",
                "toplam_oge",
                "varsayilan_batch_boyutu",
            ],
        },
        "VersionRequest": {
            "type": "object",
            "properties": {"beklenen_version": {"type": "integer", "minimum": 1}},
            "required": ["beklenen_version"],
        },
        "ReplayAdimRequest": {
            "type": "object",
            "properties": {
                "beklenen_version": {"type": "integer", "minimum": 1},
                "batch_boyutu": {"type": "integer", "minimum": 1, "maximum": 25},
            },
            "required": ["beklenen_version"],
        },
        "ConfusionMatrix": {
            "type": "object",
            "properties": {
                "true_negative": {"type": "integer"},
                "false_positive": {"type": "integer"},
                "false_negative": {"type": "integer"},
                "true_positive": {"type": "integer"},
            },
        },
        "ReplayMetrics": {
            "type": "object",
            "properties": {
                "precision": {"type": "number", "nullable": True},
                "recall": {"type": "number", "nullable": True},
                "f1": {"type": "number", "nullable": True},
                "pr_auc": {"type": "number", "nullable": True},
                "confusion_matrix": _ref("ConfusionMatrix"),
            },
        },
        "ReplayDetay": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "durum": {
                    "type": "string",
                    "enum": [
                        "HAZIR",
                        "CALISIYOR",
                        "DURAKLATILDI",
                        "TAMAMLANDI",
                        "IPTAL_EDILDI",
                    ],
                },
                "toplam_oge": {"type": "integer"},
                "metrikler": _ref("ReplayMetrics"),
            },
        },
    }
    return {
        "securitySchemes": {
            "jwtAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "schemas": schemas,
        "responses": {
            "StandartHata": {
                "description": "Standart güvenli hata sözleşmesi",
                "content": {
                    "application/json": {
                        "schema": _ref("StandartHata"),
                        "examples": {
                            "validation": {
                                "value": {
                                    "hata": {
                                        "kod": "GECERSIZ_ISTEK",
                                        "mesaj": "İstek doğrulanamadı.",
                                        "alanlar": {"alan": ["Geçersiz değer."]},
                                        "trace_id": None,
                                    }
                                }
                            },
                            "permission": {
                                "value": {
                                    "hata": {
                                        "kod": "YETKI_REDDEDILDI",
                                        "mesaj": "Bu işlem için yetkiniz yok.",
                                        "alanlar": {},
                                        "trace_id": None,
                                    }
                                }
                            },
                            "conflict": {
                                "value": {
                                    "hata": {
                                        "kod": "KAYNAK_CAKISMASI",
                                        "mesaj": "Kaynak güncel değil.",
                                        "alanlar": {},
                                        "trace_id": None,
                                    }
                                }
                            },
                            "unavailable": {
                                "value": {
                                    "hata": {
                                        "kod": "HIZMET_KULLANILAMIYOR",
                                        "mesaj": "Hizmet geçici olarak kullanılamıyor.",
                                        "alanlar": {},
                                        "trace_id": None,
                                    }
                                }
                            },
                        },
                    }
                },
            }
        },
    }


class ProjectSchemaGenerator(SchemaGenerator):
    def get_schema(self, request=None, public=False):
        return build_openapi_schema()
