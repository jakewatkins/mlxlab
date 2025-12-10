# Create Unit Tests for .NET Solution

## Goal
Generate unit tests for each public method in every class across all projects in a .NET solution using xUnit.

## Instructions
- Use the latest version of the NuGet package `xunit`.
- If no `.sln` file is found, stop and prompt the developer to create one. This is a strict requirement.
- For each project in the solution, create a corresponding test project named `{ProjectName}.Test`.
- Analyze each class to identify its dependencies. Create a test fixture that initializes the class using **real instances** of its dependencies. Do **not** use mocks.
- For each public method:
  - Write unit tests using the **Arrange-Act-Assert (AAA)** pattern.
  - Include enough test cases to achieve **at least 50% code coverage**.

## Output Format
- Create one test class per source class.
- Use `[Fact]` and `[Theory]` attributes appropriately.
- Include inline comments to explain the purpose of each test.

## Example
```csharp
public class Calculator
{
    public int Add(int a, int b) => a + b;
    public int Multiply(int a, int b) => a * b;
}

Expected test output:

public class CalculatorTests
{
    [Fact]
    public void Add_ReturnsCorrectSum()
    {
        // Arrange
        var calculator = new Calculator();

        // Act
        var result = calculator.Add(2, 3);

        // Assert
        Assert.Equal(5, result);
    }

    [Theory]
    [InlineData(2, 3, 6)]
    [InlineData(0, 5, 0)]
    public void Multiply_ReturnsCorrectProduct(int a, int b, int expected)
    {
        // Arrange
        var calculator = new Calculator();

        // Act
        var result = calculator.Multiply(a, b);

        // Assert
        Assert.Equal(expected, result);
    }
}