# Common Error Patterns and Solutions

This reference contains common error patterns across different programming languages and frameworks, along with their solutions.

## JavaScript/Node.js Errors

### 1. TypeError: Cannot read property 'x' of undefined/null
**Pattern**: `Cannot read property 'length' of undefined`
**Cause**: Trying to access a property of a null or undefined value
**Solutions**:
- Add null/undefined checks before accessing properties
- Use optional chaining: `obj?.prop?.length`
- Initialize variables properly before use

```javascript
// Before
const length = myArray.length; // Error if myArray is undefined

// After
const length = myArray?.length || 0; // Safe access
// or
const length = myArray ? myArray.length : 0;
```

### 2. ReferenceError: x is not defined
**Pattern**: `ReferenceError: myVariable is not defined`
**Cause**: Using a variable that hasn't been declared
**Solutions**:
- Declare the variable before using it
- Check for typos in variable names
- Ensure proper variable scope

### 3. SyntaxError: Unexpected token
**Pattern**: `SyntaxError: Unexpected token '}'`
**Cause**: Missing or extra syntax elements
**Solutions**:
- Check for missing commas, brackets, or parentheses
- Verify proper indentation and formatting
- Use a linter to catch syntax errors

## Python Errors

### 1. NameError: name 'x' is not defined
**Pattern**: `NameError: name 'requests' is not defined`
**Cause**: Using a variable or module that hasn't been imported/defined
**Solutions**:
- Import the required module: `import requests`
- Check variable scope and declaration
- Verify module installation

### 2. AttributeError: 'x' object has no attribute 'y'
**Pattern**: `AttributeError: 'NoneType' object has no attribute 'append'`
**Cause**: Trying to access an attribute on a None object
**Solutions**:
- Check if object is None before accessing attributes
- Ensure proper initialization of objects

```python
# Before
result = my_list.append(item)  # Error if my_list is None

# After
if my_list is not None:
    my_list.append(item)
# or
my_list = my_list or []
my_list.append(item)
```

### 3. IndexError: list index out of range
**Pattern**: `IndexError: list index out of range`
**Cause**: Accessing an index that doesn't exist in a list
**Solutions**:
- Check list length before accessing by index
- Use bounds checking: `if index < len(my_list)`

## Java Errors

### 1. NullPointerException
**Pattern**: `java.lang.NullPointerException`
**Cause**: Calling a method or accessing a property on a null object
**Solutions**:
- Add null checks before method calls
- Initialize objects properly
- Use Optional class when appropriate

```java
// Before
String length = myString.length(); // NPE if myString is null

// After
if (myString != null) {
    String length = myString.length();
}
// or
String length = Optional.ofNullable(myString).map(String::length).orElse(0);
```

### 2. ArrayIndexOutOfBoundsException
**Pattern**: `java.lang.ArrayIndexOutOfBoundsException: Index 5 out of bounds for length 3`
**Cause**: Accessing an array index that doesn't exist
**Solutions**:
- Check array bounds before accessing
- Use proper loop conditions

### 3. ClassNotFoundException
**Pattern**: `java.lang.ClassNotFoundException: com.example.MyClass`
**Cause**: Missing class in classpath
**Solutions**:
- Verify classpath configuration
- Check for missing dependencies
- Ensure proper package structure

## Database Errors

### 1. Connection Errors
**Pattern**: `SQLSTATE[HY000] [2002] Connection refused`
**Cause**: Database server is down or connection parameters are incorrect
**Solutions**:
- Check database server status
- Verify connection parameters (host, port, credentials)
- Check network connectivity

### 2. SQL Syntax Errors
**Pattern**: `You have an error in your SQL syntax; check the manual...`
**Cause**: Incorrect SQL syntax
**Solutions**:
- Verify SQL syntax against database documentation
- Use parameterized queries to avoid syntax issues
- Check for reserved words used as identifiers

### 3. Foreign Key Constraint Violations
**Pattern**: `Cannot add or update a child row: a foreign key constraint fails`
**Cause**: Referencing a non-existent record in a related table
**Solutions**:
- Ensure referenced records exist before creating dependent records
- Check for proper transaction handling
- Verify data integrity

## Web/HTTP Errors

### 1. 404 Not Found
**Pattern**: `404: The requested resource could not be found`
**Cause**: Resource doesn't exist or URL is incorrect
**Solutions**:
- Verify the URL is correct
- Check routing configuration
- Ensure the resource exists

### 2. 500 Internal Server Error
**Pattern**: `500: Internal Server Error`
**Cause**: Server-side error occurred
**Solutions**:
- Check server logs for details
- Verify server configuration
- Debug the application code

### 3. CORS Errors
**Pattern**: `Access to fetch at 'x' from origin 'y' has been blocked by CORS policy`
**Cause**: Cross-origin request blocked by CORS policy
**Solutions**:
- Configure CORS headers on the server
- Add appropriate CORS middleware
- Check allowed origins configuration

## Common Debugging Techniques

### 1. Log Analysis
- Look for error timestamps and patterns
- Identify the sequence of events leading to the error
- Check for related warnings before the error

### 2. Stack Trace Reading
- Start from the bottom (root cause) and work up
- Look for application code in the stack
- Identify the error source and propagation path

### 3. Input Validation
- Check data types and formats
- Verify required fields are present
- Look for unexpected null or empty values

### 4. Environment Issues
- Verify configuration settings
- Check for missing environment variables
- Ensure proper permissions and access rights

## Error Prevention Strategies

### 1. Defensive Programming
- Add input validation
- Use try-catch blocks appropriately
- Implement proper error handling

### 2. Logging Best Practices
- Log error context and relevant variables
- Use appropriate log levels
- Include timestamps and unique identifiers

### 3. Testing Strategies
- Write unit tests for edge cases
- Implement integration tests
- Use automated testing tools