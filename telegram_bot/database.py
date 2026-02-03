import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(Config.DATABASE_URL)
        self.create_tables()
        self.update_tables()
    
    def create_tables(self):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username VARCHAR(100),
                    address TEXT NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    task TEXT NOT NULL,
                    comment TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    accepted_by BIGINT,
                    accepted_username VARCHAR(100),
                    return_reason TEXT,
                    returned_by BIGINT,
                    returned_username VARCHAR(100),
                    close_reason TEXT,
                    closed_by BIGINT,
                    closed_username VARCHAR(100),
                    closed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER
                )
            """)
            self.conn.commit()
    
    def update_tables(self):
        """Обновление структуры существующих таблиц"""
        with self.conn.cursor() as cursor:
            try:
                # Проверяем существование новых колонок и добавляем их при необходимости
                cursor.execute("""
                    DO $$
                    BEGIN
                        -- Проверяем существование колонки return_reason
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='return_reason'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN return_reason TEXT;
                        END IF;
                        
                        -- Проверяем существование колонки returned_by
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='returned_by'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN returned_by BIGINT;
                        END IF;
                        
                        -- Проверяем существование колонки returned_username
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='returned_username'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN returned_username VARCHAR(100);
                        END IF;
                        
                        -- Проверяем существование колонки close_reason
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='close_reason'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN close_reason TEXT;
                        END IF;
                        
                        -- Проверяем существование колонки closed_by
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='closed_by'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN closed_by BIGINT;
                        END IF;
                        
                        -- Проверяем существование колонки closed_username
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='closed_username'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN closed_username VARCHAR(100);
                        END IF;
                        
                        -- Проверяем существование колонки closed_at
                        IF NOT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name='applications' 
                            AND column_name='closed_at'
                        ) THEN
                            ALTER TABLE applications ADD COLUMN closed_at TIMESTAMP;
                        END IF;
                    END $$;
                """)
                self.conn.commit()
                print("Таблица 'applications' успешно обновлена")
            except Exception as e:
                print(f"Ошибка при обновлении таблицы: {e}")
                self.conn.rollback()
    
    def create_application(self, application):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO applications 
                (user_id, username, address, phone, task, comment, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (application.user_id, application.username, 
                  application.address, application.phone, 
                  application.task, application.comment, 
                  application.status))
            app_id = cursor.fetchone()[0]
            self.conn.commit()
            return app_id
    
    def get_application(self, app_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM applications WHERE id = %s", (app_id,))
            return cursor.fetchone()
    
    def accept_application(self, app_id, user_id, username):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE applications 
                SET status = 'accepted', 
                    accepted_by = %s, 
                    accepted_username = %s,
                    return_reason = NULL,
                    returned_by = NULL,
                    returned_username = NULL,
                    close_reason = NULL,
                    closed_by = NULL,
                    closed_username = NULL,
                    closed_at = NULL
                WHERE id = %s
                RETURNING id
            """, (user_id, username, app_id))
            result = cursor.fetchone()
            self.conn.commit()
            return result is not None
    
    def return_application(self, app_id, user_id, username, reason):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE applications 
                SET status = 'pending', 
                    return_reason = %s,
                    returned_by = %s,
                    returned_username = %s,
                    close_reason = NULL,
                    closed_by = NULL,
                    closed_username = NULL,
                    closed_at = NULL
                WHERE id = %s
                RETURNING id
            """, (reason, user_id, username, app_id))
            result = cursor.fetchone()
            self.conn.commit()
            return result is not None
    
    def close_application(self, app_id, user_id, username, reason):
        """Закрытие заявки"""
        with self.conn.cursor() as cursor:
            from datetime import datetime
            cursor.execute("""
                UPDATE applications 
                SET status = 'closed', 
                    close_reason = %s,
                    closed_by = %s,
                    closed_username = %s,
                    closed_at = %s
                WHERE id = %s
                RETURNING id
            """, (reason, user_id, username, datetime.now(), app_id))
            result = cursor.fetchone()
            self.conn.commit()
            return result is not None
    
    def set_message_id(self, app_id, message_id):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE applications 
                SET message_id = %s 
                WHERE id = %s
            """, (message_id, app_id))
            self.conn.commit()
    
    def get_pending_applications(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM applications WHERE status = 'pending'")
            return cursor.fetchall()

    def check_application_owner(self, app_id, user_id):
        """Проверяет, принял ли пользователь заявку"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT accepted_by FROM applications 
                WHERE id = %s AND accepted_by = %s AND status = 'accepted'
            """, (app_id, user_id))
            result = cursor.fetchone()
            return result is not None
    

db = Database()