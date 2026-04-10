# E-Invoicing System

A comprehensive digital invoicing solution for Pakistan's Federal Board of Revenue (FBR) e-invoicing system, featuring automated bulk invoice processing and real-time FBR integration.

## Features

### Core Invoicing
- **Manual Invoice Creation**: Create and submit individual invoices through an intuitive web interface
- **FBR Integration**: Direct integration with FBR's e-invoicing API (Sandbox and Production)
- **Invoice Validation**: Real-time validation against FBR schema before submission
- **Multi-Environment Support**: Switch between Sandbox and Production environments
- **Invoice History**: Track all submitted invoices with detailed status information

### Automation (NEW)
- **Bulk Excel Upload**: Upload up to 1,000 invoices at once using Excel templates
- **Scheduled Processing**: Schedule invoices for automatic submission at specific times
- **FTE Worker**: Background worker that processes invoices hourly without manual intervention
- **Dashboard Monitoring**: Real-time statistics and filtering for automated invoices
- **Status Tracking**: Monitor validation, submission, and failure status for each invoice
- **Export Results**: Download processed invoices with updated status and error details

### User Management
- **Authentication**: Secure JWT-based authentication
- **User Profiles**: Manage user information and preferences
- **Row-Level Security**: Users can only access their own invoices and data

## Architecture

### Tech Stack

**Backend**:
- FastAPI (Python 3.11+)
- PostgreSQL (Database)
- SQLModel (ORM)
- Alembic (Migrations)
- APScheduler (Background Jobs)
- Pandas + OpenPyXL (Excel Processing)

**Frontend**:
- Next.js 15 (React)
- TypeScript
- Tailwind CSS
- Shadcn/ui Components

**Infrastructure**:
- Docker (Containerization)
- systemd (Worker Service Management)

### Project Structure

```
E-Invoicing/
├── backend/                 # FastAPI backend
│   ├── src/
│   │   ├── api/            # API endpoints
│   │   │   └── v1/
│   │   │       ├── invoices.py
│   │   │       ├── masterdata.py
│   │   │       └── automation/
│   │   │           ├── excel.py
│   │   │           ├── dashboard.py
│   │   │           ├── retry.py
│   │   │           └── health.py
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   │   ├── fbr_client.py
│   │   │   ├── excel_service.py
│   │   │   ├── automation_service.py
│   │   │   └── fte_worker_service.py
│   │   ├── workers/        # Background workers
│   │   │   └── fte_worker.py
│   │   └── utils/          # Utilities
│   ├── alembic/            # Database migrations
│   └── tests/              # Unit and integration tests
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   └── services/      # API clients
├── docs/                   # Documentation
│   ├── FTE_WORKER_DEPLOYMENT.md
│   └── EXCEL_TEMPLATE_SPECS.md
└── specs/                  # Feature specifications
    └── 001-invoice-automation/
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd E-Invoicing/backend
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Required environment variables:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/einvoicing
   JWT_SECRET_KEY=your-secret-key
   FBR_SANDBOX_URL=https://sandbox.fbr.gov.pk/api
   FBR_PRODUCTION_URL=https://api.fbr.gov.pk
   FBR_API_KEY=your-fbr-api-key
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the backend server**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

   API will be available at: `http://localhost:8000`
   API docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

   Required environment variables:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

   Frontend will be available at: `http://localhost:3000`

### FTE Worker Setup (Optional - for automation)

The FTE worker processes scheduled invoices automatically every hour.

**Development**:
```bash
cd backend
python -m src.workers.fte_worker
```

**Production**: See [FTE Worker Deployment Guide](docs/FTE_WORKER_DEPLOYMENT.md)

## Usage

### Manual Invoice Creation

1. Login to the web interface
2. Navigate to "Create Invoice"
3. Fill in invoice details (seller, buyer, items)
4. Select environment (Sandbox/Production)
5. Submit to FBR
6. View status in invoice history

### Automated Bulk Processing

1. **Download Template**
   - Navigate to "Automation" page
   - Click "Download Template"
   - Excel file with predefined columns will download

2. **Fill Invoice Data**
   - Open template in Excel
   - Delete sample row
   - Add your invoice data (up to 1,000 rows)
   - Set scheduled date and time for each invoice
   - See [Excel Template Specs](docs/EXCEL_TEMPLATE_SPECS.md) for column details

3. **Upload File**
   - Click "Upload Excel"
   - Select your filled template
   - System validates and stores invoices
   - Concurrent uploads are blocked per user

4. **Monitor Processing**
   - View dashboard for real-time statistics
   - Filter by status, date range, or source
   - Check individual invoice details
   - Download results with updated status

5. **Automatic Processing**
   - FTE worker runs every hour (at minute 0)
   - Validates pending invoices
   - Submits valid invoices to FBR
   - Updates status and logs results
   - Failed invoices can be retried manually

## API Documentation

### Authentication

All protected endpoints require JWT token in Authorization header:
```bash
Authorization: Bearer <token>
```

### Core Endpoints

**Invoices**:
- `POST /api/v1/invoices` - Create manual invoice
- `GET /api/v1/invoices` - List user's invoices
- `GET /api/v1/invoices/{id}` - Get invoice details
- `POST /api/v1/invoices/{id}/validate` - Validate invoice
- `POST /api/v1/invoices/{id}/submit` - Submit to FBR

**Automation**:
- `GET /api/v1/automation/template/download` - Download Excel template
- `POST /api/v1/automation/excel/upload` - Upload filled Excel (rate limited: 5/hour)
- `GET /api/v1/automation/excel/status/{session_id}` - Check upload status
- `GET /api/v1/automation/dashboard/stats` - Get dashboard statistics
- `GET /api/v1/automation/dashboard/invoices` - List automated invoices (paginated)
- `GET /api/v1/automation/dashboard/invoice/{id}` - Get invoice details with logs
- `GET /api/v1/automation/dashboard/download/{session_id}` - Download results
- `POST /api/v1/automation/invoice/{id}/retry` - Retry failed invoice
- `GET /api/v1/automation/health/worker` - Check FTE worker health
- `GET /api/v1/automation/health/status` - System health status

**Master Data**:
- `GET /api/v1/masterdata/provinces` - List provinces
- `GET /api/v1/masterdata/uoms` - List units of measurement
- `GET /api/v1/masterdata/tax-rates` - List tax rates

Full API documentation available at: `http://localhost:8000/docs`

## Database Schema

### Core Tables

- `users` - User accounts and authentication
- `invoices` - Manual invoices
- `invoice_items` - Line items for manual invoices

### Automation Tables

- `automation_invoice` - Automated invoices from Excel
- `excel_upload_session` - Excel upload tracking
- `automation_log` - Activity logs for automation

### Indexes

Optimized indexes for:
- User data isolation (`user_id`)
- Hourly worker queries (`status`, `scheduled_date`, `scheduled_time`)
- Invoice number uniqueness per user
- Dashboard filtering and pagination

## Deployment

### Backend Deployment

1. **Build Docker image**
   ```bash
   cd backend
   docker build -t einvoicing-backend .
   ```

2. **Run container**
   ```bash
   docker run -d \
     --name einvoicing-backend \
     -p 8000:8000 \
     --env-file .env \
     einvoicing-backend
   ```

3. **Deploy FTE Worker**
   - See [FTE Worker Deployment Guide](docs/FTE_WORKER_DEPLOYMENT.md)
   - Configure as systemd service (Linux) or Windows Service

### Frontend Deployment

1. **Build production bundle**
   ```bash
   cd frontend
   npm run build
   ```

2. **Start production server**
   ```bash
   npm start
   ```

3. **Deploy to Vercel/Netlify** (recommended)
   ```bash
   vercel deploy --prod
   ```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

### End-to-End Testing

See `specs/001-invoice-automation/quickstart.md` for complete testing checklist.

## Monitoring

### Health Checks

- **API Health**: `GET /health`
- **Worker Health**: `GET /api/v1/automation/health/worker`
- **System Status**: `GET /api/v1/automation/health/status`

### Logs

- **Backend**: `uvicorn` logs to stdout
- **FTE Worker**: Logs to `fte_worker.log` and `/var/log/fte-worker/`
- **Database**: Activity logs in `automation_log` table

### Metrics

Dashboard provides real-time metrics:
- Total invoices processed
- Success/failure rates
- Pending invoices count
- Recent activity (24 hours)

## Security

- **Authentication**: JWT tokens with expiration
- **Authorization**: Row-level security (users can only access their own data)
- **Rate Limiting**: Upload endpoint limited to 5 requests/hour per IP
- **Input Validation**: All inputs validated against schemas
- **SQL Injection**: Protected by SQLModel ORM
- **File Upload**: Size limits (10 MB) and type validation (.xlsx only)
- **Environment Isolation**: Separate Sandbox and Production credentials

## Performance

- **Database Indexes**: Optimized for common queries
- **Pagination**: All list endpoints support pagination
- **Async Processing**: FBR API calls use async/await
- **Connection Pooling**: Database connection pool configured
- **File Processing**: In-memory Excel parsing (no disk I/O)
- **Batch Limits**: 1,000 invoices per upload

## Troubleshooting

### Common Issues

**Database Connection Failed**:
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify credentials and database exists

**FBR API Errors**:
- Check `FBR_API_KEY` is valid
- Verify environment (SANDBOX vs PRODUCTION)
- Review FBR API status

**Worker Not Processing**:
- Check worker is running: `systemctl status fte-worker`
- Review worker logs: `journalctl -u fte-worker -f`
- Verify scheduled times are in the future
- Check health endpoint: `/api/v1/automation/health/worker`

**Upload Fails**:
- Verify Excel file format (.xlsx)
- Check file size (< 10 MB)
- Ensure all required columns present
- Review validation errors in response

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Documentation

- [FTE Worker Deployment Guide](docs/FTE_WORKER_DEPLOYMENT.md)
- [Excel Template Specifications](docs/EXCEL_TEMPLATE_SPECS.md)
- [Feature Specification](specs/001-invoice-automation/spec.md)
- [Implementation Plan](specs/001-invoice-automation/plan.md)
- [Task Breakdown](specs/001-invoice-automation/tasks.md)

## License

[Your License Here]

## Support

For issues or questions:
- Check documentation in `docs/` directory
- Review API documentation at `/docs` endpoint
- Check health endpoints for system status
- Review logs for error details

## Changelog

### v2.0.0 - Invoice Automation (2026-04-09)
- Added bulk Excel upload for invoices
- Implemented FTE worker for automated processing
- Added automation dashboard with real-time statistics
- Implemented scheduled invoice processing
- Added health check endpoints for monitoring
- Optimized database queries for 10,000+ invoices
- Added rate limiting to upload endpoint
- Implemented row-level security across all endpoints

### v1.0.0 - Initial Release
- Manual invoice creation and submission
- FBR API integration (Sandbox and Production)
- User authentication and authorization
- Invoice validation and history
- Master data management
