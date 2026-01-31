# Web UI for Compliance Reports

## Accessing the UI

Once the Flask application is running, access the web interface at:

```
http://localhost:5000/compliance
```

## Features

### Modern Responsive Design
- Beautiful gradient UI with purple/blue theme
- Mobile-friendly responsive layout
- Smooth animations and transitions

### Report Generation
- **Date Range Selection**: Pick start and end dates with calendar UI
- **Team Filtering**: Optional dropdown to filter by specific team
- **Generate Button**: One-click compliance report generation
- **Demo Mode**: Generate demo reports without JIRA connection

### Progress Tracking
- **Real-time Progress Bar**: Visual indication of generation progress
- **Status Messages**: Text updates on current operation
- **Loading Spinner**: Animated indicator during processing

### Report History
- **Auto-refresh**: Report list updates after generation
- **File Information**: Shows filename, creation date, and file size
- **One-Click Download**: Direct download buttons for all reports
- **Empty State**: Helpful message when no reports exist

## Screenshots

### Main Interface
The interface includes:
- Header with title and description
- Report generation form with date pickers
- Team selection dropdown
- Two action buttons (Generate & Demo)
- Success/error alert banners

### During Generation
When generating a report:
- Buttons become disabled
- "Generating..." text with spinner appears
- Progress bar fills from 0% to 100%
- Status messages update throughout process

### Report History
The history section displays:
- List of all generated compliance reports
- Each item shows: filename, creation time, file size
- Download button for each report
- Newest reports appear first

## Usage Flow

1. **Select Date Range**
   - Start Date: Beginning of compliance period
   - End Date: End of compliance period
   - Defaults to last 4 weeks

2. **Choose Team (Optional)**
   - Select "All Teams" or specific team
   - Team list loaded from database

3. **Generate Report**
   - Click "Generate Compliance Report" for real data
   - OR click "Generate Demo Report" for sample data

4. **Wait for Completion**
   - Watch progress bar fill up
   - Read status messages
   - Report appears in history when done

5. **Download Report**
   - Click download button next to desired report
   - Excel file downloads to your computer

## Technical Details

### API Integration
The UI calls these REST API endpoints:
- `POST /api/reports/compliance/generate` - Generate real report
- `POST /api/reports/compliance/demo` - Generate demo report
- `GET /api/reports/compliance/list` - List all reports
- `GET /api/reports/teams` - Load team dropdown
- `GET /api/reports/download/{filename}` - Download report file

### Progress Simulation
Since report generation is fast, the UI simulates progress:
- 0% - Starting
- 20% - Connecting to JIRA
- 60% - Processing compliance checks
- 90% - Finalizing Excel
- 100% - Complete

### Error Handling
The UI handles errors gracefully:
- Shows red error banner for failures
- Re-enables buttons after errors
- Logs errors to browser console
- Displays user-friendly error messages

## Customization

### Colors
Edit the CSS gradient in `compliance-ui.html`:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Date Defaults
Change default date range in JavaScript:
```javascript
fourWeeksAgo.setDate(today.getDate() - 28);  // Change -28 to desired days
```

### Progress Steps
Modify progress percentages and messages:
```javascript
updateProgress(20, 'Your custom message...');
```

## Browser Compatibility
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development
To modify the UI:
1. Edit `static/compliance-ui.html`
2. Save changes
3. Refresh browser (hard refresh: Ctrl+F5 or Cmd+Shift+R)
4. No server restart needed for HTML/CSS/JS changes
