"""
Test configuration and fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mutation_parser import MutationParser
from core.mutation_applier import MutationApplier
from core.coverage_runner import CoverageRunner


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    test_dir = Path(tempfile.mkdtemp())
    yield test_dir
    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def sample_mutations_log_content():
    """Sample mutants.log content for testing"""
    return """# This is a comment
1:VOID_METHOD_CALLS:org.example.Test.voidMethod()V:org.example.Test.voidMethod()V:org.example.Test@testMethod:10:someObject.voidMethod() |==> 
2:CONDITIONALS_BOUNDARY:org.example.Test.test(I)Z:org.example.Test.test(I)Z:org.example.Test@test:15:x > 0 |==> x >= 0
3:INCREMENTS:org.example.Test.increment()V:org.example.Test.increment()V:org.example.Test@increment:20:i++ |==> i--
4:MATH:org.example.Test.calc()I:org.example.Test.calc()I:org.example.Test@calc:25:result * 2 |==> result * 3
"""


@pytest.fixture
def sample_mutations_log_file(temp_dir, sample_mutations_log_content):
    """Create a sample mutants.log file"""
    log_file = temp_dir / "mutants.log"
    with open(log_file, 'w') as f:
        f.write(sample_mutations_log_content)
    return log_file


@pytest.fixture
def sample_java_file_content():
    """Sample Java file content for mutation testing"""
    return """package org.example;

public class Test {
    public void voidMethod() {
        someObject.voidMethod();
    }
    
    public boolean test(int x) {
        return x > 0;
    }
    
    public void increment() {
        int i = 0;
        i++;
    }
    
    public int calc() {
        int result = 5;
        return result * 2;
    }
}
"""


@pytest.fixture
def sample_java_file(temp_dir, sample_java_file_content):
    """Create a sample Java file for testing"""
    java_dir = temp_dir / "src" / "main" / "java" / "org" / "example"
    java_dir.mkdir(parents=True)
    java_file = java_dir / "Test.java"
    with open(java_file, 'w') as f:
        f.write(sample_java_file_content)
    return java_file


@pytest.fixture
def mutation_parser():
    return MutationParser()


@pytest.fixture
def mutation_applier():
    return MutationApplier(random_seed=42)


@pytest.fixture
def coverage_runner():
    return CoverageRunner()