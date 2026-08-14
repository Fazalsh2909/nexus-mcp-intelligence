from app.orchestration.tools_postgres import _validate_query


class TestSQLValidation:
    def test_allows_select(self):
        assert _validate_query("SELECT * FROM users") is True

    def test_allows_select_with_where(self):
        assert _validate_query("SELECT name FROM users WHERE id = 1") is True

    def test_allows_cte(self):
        assert (
            _validate_query("WITH cte AS (SELECT * FROM users) SELECT * FROM cte")
            is True
        )

    def test_rejects_insert(self):
        assert _validate_query("INSERT INTO users (name) VALUES ('hacker')") is False

    def test_rejects_update(self):
        assert _validate_query("UPDATE users SET name = 'hacked'") is False

    def test_rejects_delete(self):
        assert _validate_query("DELETE FROM users") is False

    def test_rejects_drop(self):
        assert _validate_query("DROP TABLE users") is False

    def test_rejects_alter(self):
        assert _validate_query("ALTER TABLE users ADD COLUMN evil TEXT") is False

    def test_rejects_truncate(self):
        assert _validate_query("TRUNCATE TABLE users") is False

    def test_rejects_stacked_queries(self):
        assert _validate_query("SELECT * FROM users; DROP TABLE users") is False

    def test_rejects_comment(self):
        assert _validate_query("SELECT * FROM users -- WHERE 1=1") is False

    def test_rejects_block_comment(self):
        assert _validate_query("SELECT * FROM users /* bypass */") is False

    def test_rejects_create(self):
        assert _validate_query("CREATE TABLE evil (id INT)") is False

    def test_rejects_grant(self):
        assert _validate_query("GRANT ALL ON users TO hacker") is False
