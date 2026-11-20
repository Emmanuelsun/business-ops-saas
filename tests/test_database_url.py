from app.database import normalize_database_url


def test_plain_postgresql_address_gets_the_psycopg2_driver():
    url = "postgresql://user:pass@host:5432/dbname?sslmode=require"
    assert normalize_database_url(url) == (
        "postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require"
    )


def test_old_postgres_scheme_is_understood():
    url = "postgres://user:pass@host:5432/dbname"
    assert normalize_database_url(url) == (
        "postgresql+psycopg2://user:pass@host:5432/dbname"
    )


def test_address_that_already_names_a_driver_is_left_alone():
    url = "postgresql+psycopg2://user:pass@host:5432/dbname"
    assert normalize_database_url(url) == url


# End of file.