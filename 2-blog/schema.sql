CREATE TABLE IF NOT EXISTS articles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(190) NOT NULL UNIQUE,
  title VARCHAR(300) NOT NULL,
  excerpt TEXT,
  content MEDIUMTEXT NOT NULL,
  category VARCHAR(40) NOT NULL DEFAULT 'technology',
  status ENUM('draft','published') NOT NULL DEFAULT 'draft',
  meta_description VARCHAR(300),
  image_url TEXT, image_alt VARCHAR(300), image_credit VARCHAR(200),
  image_credit_url TEXT, image_license VARCHAR(100),
  sources_json TEXT,
  views INT NOT NULL DEFAULT 0,
  published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_pub (status, published_at), KEY idx_cat (category, status),
  FULLTEXT KEY ft_search (title, excerpt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS idempotency_keys (
  k VARCHAR(190) PRIMARY KEY,
  slug VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sync_state (
  id TINYINT PRIMARY KEY, last_run INT NOT NULL DEFAULT 0, last_status VARCHAR(200)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT IGNORE INTO sync_state (id,last_run) VALUES (1,0);
