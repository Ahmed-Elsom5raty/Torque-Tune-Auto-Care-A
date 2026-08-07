CREATE TABLE Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    role NVARCHAR(20) NOT NULL CHECK (role IN ('technician', 'manager')),
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);

CREATE TABLE Categories (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(50) NOT NULL UNIQUE,
    description NVARCHAR(200) NULL
);

CREATE TABLE Suppliers (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    phone NVARCHAR(20) NULL,
    email NVARCHAR(100) NULL,
    address NVARCHAR(200) NULL
);

CREATE TABLE SpareParts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    part_name NVARCHAR(100) NOT NULL,
    part_number NVARCHAR(50) NOT NULL UNIQUE,
    category_id INT NOT NULL,
    supplier_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity >= 0),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    location NVARCHAR(50) NOT NULL,
    minimum_stock INT NOT NULL DEFAULT 5 CHECK (minimum_stock >= 0),
    status NVARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'discontinued')),
    FOREIGN KEY (category_id) REFERENCES Categories(id),
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id)
);

CREATE TABLE AlternativeParts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    part_id INT NOT NULL,
    alternative_part_id INT NOT NULL,
    FOREIGN KEY (part_id) REFERENCES SpareParts(id),
    FOREIGN KEY (alternative_part_id) REFERENCES SpareParts(id)
);

CREATE TABLE InventoryLogs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    part_id INT NOT NULL,
    user_id INT NOT NULL,
    old_quantity INT NOT NULL,
    new_quantity INT NOT NULL,
    action NVARCHAR(20) NOT NULL CHECK (action IN ('increase', 'decrease', 'set')),
    reason NVARCHAR(300) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (part_id) REFERENCES SpareParts(id),
    FOREIGN KEY (user_id) REFERENCES Users(id)
);

-- ---------------------------------------------------------
-- AI Agent Memory Tables (Added for Long-Term Persistence)
-- ---------------------------------------------------------

-- Stores significant events and actions (Promoted from Short-Term Memory)
CREATE TABLE EpisodicMemory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    event_type NVARCHAR(100) NOT NULL,
    content NVARCHAR(MAX) NOT NULL, -- Stores the JSON representation of the event/action
    promotion_reason NVARCHAR(500) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);

-- Stores consolidated long-term knowledge and user facts with version control
CREATE TABLE SemanticMemory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    fact_key NVARCHAR(100) NOT NULL,
    fact_value NVARCHAR(MAX) NOT NULL, -- Stores the value (e.g., preferred setting)
    version INT NOT NULL DEFAULT 1,
    is_active BIT NOT NULL DEFAULT 1, -- 1 (True) for current active facts, 0 (False) for history
    updated_at DATETIME NOT NULL DEFAULT GETDATE()
);