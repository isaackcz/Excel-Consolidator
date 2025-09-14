/**
 * Excel Consolidator Error Reporting - Enhanced Version
 * 
 * This script provides a professional error reporting system with:
 * - Proper sheet structure and formatting
 * - Data validation and organization
 * - Summary statistics and analytics
 * - Better error categorization
 * 
 * Setup Instructions:
 * 1. Go to https://script.google.com/
 * 2. Create a new project
 * 3. Replace the default code with this script
 * 4. Save and deploy as a web app
 * 5. Set permissions to "Anyone" and "Execute as: Me"
 * 6. Copy the web app URL and use it in your config.py
 */

function doPost(e) {
  try {
    // Parse the incoming JSON data
    const data = JSON.parse(e.postData.contents);
    
    // Validate required fields
    if (!data.spreadsheet_id || !data.data) {
      return ContentService
        .createTextOutput(JSON.stringify({
          success: false,
          error: "Missing required fields: spreadsheet_id and data"
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Open the spreadsheet
    const spreadsheet = SpreadsheetApp.openById(data.spreadsheet_id);
    let sheet = spreadsheet.getSheetByName(data.sheet_name || 'Error Log');
    
    // Create sheet if it doesn't exist
    if (!sheet) {
      sheet = spreadsheet.insertSheet(data.sheet_name || 'Error Log');
      setupSheetStructure(sheet);
    }
    
    // Add the error data
    const rows = data.data;
    if (rows && rows.length > 0) {
      const lastRow = sheet.getLastRow();
      const startRow = lastRow + 1;
      const numRows = rows.length;
      const numCols = rows[0].length;
      
      // Add data rows
      sheet.getRange(startRow, 1, numRows, numCols).setValues(rows);
      
      // Apply formatting to new rows
      formatDataRows(sheet, startRow, numRows, numCols);
      
      // Update summary statistics
      updateSummaryStats(sheet);
    }
    
    // Return success response
    return ContentService
      .createTextOutput(JSON.stringify({
        success: true,
        message: `Added ${rows.length} row(s) to spreadsheet`,
        timestamp: new Date().toISOString(),
        total_errors: sheet.getLastRow() - 1
      }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    // Return error response
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        error: error.toString(),
        timestamp: new Date().toISOString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function setupSheetStructure(sheet) {
  /**
   * Set up the professional sheet structure with headers and formatting
   */
  
  // Clear any existing content
  sheet.clear();
  
  // Define professional headers
  const headers = [
    'Report ID',
    'Date & Time',
    'App Version',
    'Error Category',
    'Error Type',
    'Error Message',
    'Triggered By',
    'User Count',
    'Platform',
    'Python Version',
    'Filename',
    'File Size (bytes)',
    'Stack Trace',
    'Status',
    'Notes'
  ];
  
  // Add headers to row 1
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Format header row
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setFontWeight('bold');
  headerRange.setFontSize(11);
  headerRange.setBackground('#1f4e79'); // Professional blue
  headerRange.setFontColor('white');
  headerRange.setHorizontalAlignment('center');
  headerRange.setVerticalAlignment('middle');
  
  // Set column widths for better readability
  const columnWidths = [120, 150, 80, 120, 120, 200, 150, 80, 120, 120, 150, 100, 300, 80, 200];
  for (let i = 0; i < columnWidths.length; i++) {
    sheet.setColumnWidth(i + 1, columnWidths[i]);
  }
  
  // Freeze header row
  sheet.setFrozenRows(1);
  
  // Add data validation for Status column
  const statusRange = sheet.getRange(2, 14, 1000, 1); // Column N (Status)
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['New', 'Investigating', 'Fixed', 'Won\'t Fix', 'Duplicate'], true)
    .setAllowInvalid(false)
    .setHelpText('Select error status')
    .build();
  statusRange.setDataValidation(statusRule);
  
  // Add conditional formatting for error categories
  setupConditionalFormatting(sheet);
  
  // Add summary section
  addSummarySection(sheet);
}

function formatDataRows(sheet, startRow, numRows, numCols) {
  /**
   * Apply professional formatting to data rows
   */
  
  for (let i = 0; i < numRows; i++) {
    const rowNum = startRow + i;
    const rowRange = sheet.getRange(rowNum, 1, 1, numCols);
    
    // Alternating row colors
    if (i % 2 === 0) {
      rowRange.setBackground('#f8f9fa'); // Light gray
    } else {
      rowRange.setBackground('#ffffff'); // White
    }
    
    // Format specific columns
    if (numCols >= 2) {
      // Date & Time column (B)
      sheet.getRange(rowNum, 2, 1, 1).setNumberFormat('yyyy-mm-dd hh:mm:ss');
    }
    
    if (numCols >= 12) {
      // File Size column (L)
      sheet.getRange(rowNum, 12, 1, 1).setNumberFormat('#,##0');
    }
    
    // Set default status to 'New'
    if (numCols >= 14) {
      sheet.getRange(rowNum, 14, 1, 1).setValue('New');
    }
    
    // Text wrapping for long content
    rowRange.setWrap(true);
    rowRange.setVerticalAlignment('top');
  }
  
  // Auto-resize rows for better content visibility
  sheet.autoResizeRows(startRow, numRows);
}

function setupConditionalFormatting(sheet) {
  /**
   * Set up conditional formatting for better visual organization
   */
  
  const lastRow = sheet.getMaxRows();
  
  // Format Error Category column (D) with colors
  const categoryRange = sheet.getRange(2, 4, lastRow - 1, 1);
  
  // Template Loading Error - Red
  const templateRule = SpreadsheetApp.newConditionalFormatRule()
    .setRanges([categoryRange])
    .whenTextContains('Template Loading')
    .setBackground('#ffebee')
    .setFontColor('#c62828')
    .build();
  
  // File Processing Error - Orange
  const fileRule = SpreadsheetApp.newConditionalFormatRule()
    .setRanges([categoryRange])
    .whenTextContains('File Processing')
    .setBackground('#fff3e0')
    .setFontColor('#ef6c00')
    .build();
  
  // System Error - Purple
  const systemRule = SpreadsheetApp.newConditionalFormatRule()
    .setRanges([categoryRange])
    .whenTextContains('System')
    .setBackground('#f3e5f5')
    .setFontColor('#7b1fa2')
    .build();
  
  // Apply rules
  const rules = sheet.getConditionalFormatRules();
  rules.push(templateRule, fileRule, systemRule);
  sheet.setConditionalFormatRules(rules);
}

function addSummarySection(sheet) {
  /**
   * Add a summary section with statistics
   */
  
  const lastCol = sheet.getLastColumn();
  const summaryStartCol = lastCol + 2; // Start after a gap
  
  // Summary title
  sheet.getRange(1, summaryStartCol, 1, 3).merge();
  sheet.getRange(1, summaryStartCol).setValue('ERROR REPORTING SUMMARY');
  sheet.getRange(1, summaryStartCol).setFontWeight('bold');
  sheet.getRange(1, summaryStartCol).setFontSize(14);
  sheet.getRange(1, summaryStartCol).setBackground('#2e7d32');
  sheet.getRange(1, summaryStartCol).setFontColor('white');
  sheet.getRange(1, summaryStartCol).setHorizontalAlignment('center');
  
  // Summary statistics
  const summaryData = [
    ['Total Errors:', '=COUNTA(A:A)-1'],
    ['New Errors:', '=COUNTIF(N:N,"New")'],
    ['Fixed Errors:', '=COUNTIF(N:N,"Fixed")'],
    ['Today\'s Errors:', '=COUNTIF(B:B,">="&TODAY())'],
    ['Most Common Error:', '=INDEX(E:E,MODE(MATCH(E:E,E:E,0)))'],
    ['Last Error:', '=MAX(B:B)']
  ];
  
  for (let i = 0; i < summaryData.length; i++) {
    sheet.getRange(i + 3, summaryStartCol, 1, 2).setValues([summaryData[i]]);
    
    // Format labels
    sheet.getRange(i + 3, summaryStartCol).setFontWeight('bold');
    sheet.getRange(i + 3, summaryStartCol).setBackground('#e8f5e8');
    
    // Format values
    sheet.getRange(i + 3, summaryStartCol + 1).setBackground('#f1f8e9');
  }
  
  // Set column widths for summary
  sheet.setColumnWidth(summaryStartCol, 150);
  sheet.setColumnWidth(summaryStartCol + 1, 200);
}

function updateSummaryStats(sheet) {
  /**
   * Update summary statistics (called after adding new data)
   */
  
  // This function can be expanded to update charts, pivot tables, etc.
  // For now, the formulas in the summary section will auto-update
}

function doGet(e) {
  // Handle GET requests (for testing)
  return ContentService
    .createTextOutput(JSON.stringify({
      message: "Excel Consolidator Error Reporting Service - Enhanced",
      status: "active",
      version: "2.0",
      features: [
        "Professional formatting",
        "Error categorization",
        "Summary statistics",
        "Conditional formatting",
        "Data validation"
      ],
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}

function testConnection() {
  // Test function to verify the enhanced script works
  try {
    const spreadsheetId = "1eipG_5UgnkvQGcxpQi48fAq2ZRF_ZjtNzsliVdNkEnU";
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    let sheet = spreadsheet.getSheetByName('Error Log');
    
    // Create sheet if it doesn't exist
    if (!sheet) {
      sheet = spreadsheet.insertSheet('Error Log');
      setupSheetStructure(sheet);
    }
    
    // Add a test row with enhanced data
    const testData = [
      [
        'TEST_' + new Date().getTime(),
        new Date().toISOString(),
        '1.0.0',
        'Template Loading Error',
        'BadZipFile',
        'This is a test error from enhanced Google Apps Script',
        'Test Connection',
        '1',
        'Windows-11',
        'Python 3.13.7',
        'test.xlsx',
        '1024',
        'Test stack trace for enhanced error reporting',
        'New',
        'Test error for enhanced formatting'
      ]
    ];
    
    const lastRow = sheet.getLastRow();
    sheet.getRange(lastRow + 1, 1, 1, testData[0].length).setValues(testData);
    
    // Apply formatting to test row
    formatDataRows(sheet, lastRow + 1, 1, testData[0].length);
    
    Logger.log("Enhanced test connection successful!");
    return "Enhanced test connection successful!";
    
  } catch (error) {
    Logger.log("Enhanced test connection failed: " + error.toString());
    return "Enhanced test connection failed: " + error.toString();
  }
}

function createErrorDashboard() {
  /**
   * Create a comprehensive error dashboard (optional advanced feature)
   */
  
  try {
    const spreadsheetId = "1eipG_5UgnkvQGcxpQi48fAq2ZRF_ZjtNzsliVdNkEnU";
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    
    // Create dashboard sheet
    let dashboard = spreadsheet.getSheetByName('Error Dashboard');
    if (!dashboard) {
      dashboard = spreadsheet.insertSheet('Error Dashboard');
    }
    
    // Clear existing content
    dashboard.clear();
    
    // Add dashboard title
    dashboard.getRange(1, 1, 1, 4).merge();
    dashboard.getRange(1, 1).setValue('EXCEL CONSOLIDATOR - ERROR DASHBOARD');
    dashboard.getRange(1, 1).setFontWeight('bold');
    dashboard.getRange(1, 1).setFontSize(16);
    dashboard.getRange(1, 1).setBackground('#1565c0');
    dashboard.getRange(1, 1).setFontColor('white');
    dashboard.getRange(1, 1).setHorizontalAlignment('center');
    
    // Add dashboard content
    const dashboardData = [
      ['Metric', 'Value', 'Description', 'Last Updated'],
      ['Total Errors', '=COUNTA(\'Error Log\'!A:A)-1', 'Total number of errors reported', new Date()],
      ['New Errors', '=COUNTIF(\'Error Log\'!N:N,"New")', 'Errors awaiting investigation', new Date()],
      ['Fixed Errors', '=COUNTIF(\'Error Log\'!N:N,"Fixed")', 'Errors that have been resolved', new Date()],
      ['Error Rate (Today)', '=COUNTIF(\'Error Log\'!B:B,">="&TODAY())', 'Errors reported today', new Date()],
      ['Most Common Error', '=INDEX(\'Error Log\'!E:E,MODE(MATCH(\'Error Log\'!E:E,\'Error Log\'!E:E,0)))', 'Most frequently occurring error', new Date()]
    ];
    
    dashboard.getRange(3, 1, dashboardData.length, 4).setValues(dashboardData);
    
    // Format dashboard
    const headerRange = dashboard.getRange(3, 1, 1, 4);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#424242');
    headerRange.setFontColor('white');
    
    // Set column widths
    dashboard.setColumnWidth(1, 150);
    dashboard.setColumnWidth(2, 100);
    dashboard.setColumnWidth(3, 250);
    dashboard.setColumnWidth(4, 150);
    
    Logger.log("Error dashboard created successfully!");
    return "Error dashboard created successfully!";
    
  } catch (error) {
    Logger.log("Dashboard creation failed: " + error.toString());
    return "Dashboard creation failed: " + error.toString();
  }
}
