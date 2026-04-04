-- B-06 인증 기능 수동 마이그레이션
-- 적용 전 확인:
-- 1) users.nickname 중복 데이터 제거
-- 2) 기존 사용자에 대한 password_hash 백필 정책 수립

START TRANSACTION;

ALTER TABLE users
    ADD COLUMN password_hash VARCHAR(255) NULL;

ALTER TABLE users
    ADD CONSTRAINT uk_users_nickname UNIQUE (nickname);

CREATE TABLE refresh_tokens (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_refresh_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens (expires_at);
CREATE INDEX idx_refresh_tokens_revoked_at ON refresh_tokens (revoked_at);

COMMIT;
