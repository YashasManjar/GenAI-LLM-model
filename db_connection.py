import psycopg2
import psycopg2.extras


class DbConnection:
    def connection_to_abe_db():
        # Connect to the database
        conn = psycopg2.connect(
            host="133.33.33",
            port="xxxx",
            database="xxxxx",
            user="dxxx",
            password="xxxxx"
        )

        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
