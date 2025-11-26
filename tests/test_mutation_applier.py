"""
Tests for mutation application functionality
"""

import pytest
from pathlib import Path


class TestMutationApplier:
    """Test MutationApplier class"""
    
    def test_find_java_file_by_class(self, mutation_applier, temp_dir):
        """Test finding Java file by class name"""
        # Create proper Java file structure
        java_dir = temp_dir / "src" / "main" / "java" / "org" / "example"
        java_dir.mkdir(parents=True)
        java_file = java_dir / "Test.java"
        java_file.write_text("public class Test {}")
        
        source_dirs = [temp_dir / "src" / "main" / "java"]
        
        found_file = mutation_applier.find_java_file_by_class("org.example.Test", source_dirs)
        
        assert found_file == java_file
    
    def test_find_java_file_by_class_not_found(self, mutation_applier, temp_dir):
        """Test when Java file is not found"""
        source_dirs = [temp_dir / "src"]
        
        found_file = mutation_applier.find_java_file_by_class("org.example.NonExistent", source_dirs)
        
        assert found_file is None
    
    def test_apply_mutation_to_file_exact_match(self, mutation_applier, sample_java_file):
        """Test applying mutation with exact code match"""
        success = mutation_applier.apply_mutation_to_file(
            sample_java_file,
            line_number=3,
            original_code="        someObject.voidMethod();",
            mutated_code="        // mutated: someObject.voidMethod();"
        )
        
        assert success is True
        
        # Verify the mutation was applied
        with open(sample_java_file, 'r') as f:
            lines = f.readlines()
        
        assert "        // mutated: someObject.voidMethod();" in lines[2]
    
    def test_apply_mutation_to_file_stripped_match(self, mutation_applier, sample_java_file):
        """Test applying mutation with stripped whitespace match"""
        success = mutation_applier.apply_mutation_to_file(
            sample_java_file,
            line_number=7,
            original_code="x > 0",
            mutated_code="x >= 0"
        )
        
        assert success is True
        
        # Verify the mutation was applied
        with open(sample_java_file, 'r') as f:
            content = f.read()
        
        assert "return x >= 0;" in content
    
    def test_apply_mutation_to_file_line_out_of_range(self, mutation_applier, sample_java_file):
        """Test applying mutation to non-existent line"""
        success = mutation_applier.apply_mutation_to_file(
            sample_java_file,
            line_number=100,  # Non-existent line
            original_code="some code",
            mutated_code="mutated code"
        )
        
        assert success is False
    
    def test_apply_mutation_to_file_code_not_found(self, mutation_applier, sample_java_file):
        """Test applying mutation when original code is not found"""
        success = mutation_applier.apply_mutation_to_file(
            sample_java_file,
            line_number=3,
            original_code="nonExistentCode();",  # Not in the file
            mutated_code="mutated code"
        )
        
        assert success is False
    
    def test_create_project_copy(self, mutation_applier, temp_dir):
        """Test creating project copy"""
        # Create source directory with some files
        src_dir = temp_dir / "source"
        src_dir.mkdir()
        (src_dir / "file1.java").write_text("content1")
        (src_dir / "file2.java").write_text("content2")
        
        dest_dir = temp_dir / "destination"
        
        success = mutation_applier.create_project_copy(src_dir, dest_dir)
        
        assert success is True
        assert dest_dir.exists()
        assert (dest_dir / "file1.java").exists()
        assert (dest_dir / "file2.java").read_text() == "content2"
    
    def test_generate_unique_mutants(self, mutation_applier):
        """Test generating unique mutant combinations"""
        sample_mutations = [
            {'mutant_id': '1', 'mutator': 'VOID_METHOD_CALLS', 'class_name': 'Test', 
             'line_number': 10, 'original_code': 'code1', 'mutated_code': ''},
            {'mutant_id': '2', 'mutator': 'CONDITIONALS_BOUNDARY', 'class_name': 'Test', 
             'line_number': 15, 'original_code': 'code2', 'mutated_code': 'mutated2'},
            {'mutant_id': '3', 'mutator': 'INCREMENTS', 'class_name': 'Test', 
             'line_number': 20, 'original_code': 'code3', 'mutated_code': 'mutated3'},
        ]
        
        mutants = mutation_applier.generate_unique_mutants(
            sample_mutations, 
            num_mutants=2, 
            max_mutations=2
        )
        
        assert len(mutants) == 2
        assert 'mutant_id' in mutants[0]
        assert 'mutations' in mutants[0]
        assert 'num_mutations' in mutants[0]
        
        # Should have unique combinations
        assert mutants[0]['signature'] != mutants[1]['signature']
    
    def test_apply_multiple_mutations(self, mutation_applier, sample_java_file):
        """Test applying multiple mutations to the same file"""
        mutations = [
            {
                'line_number': 3,
                'original_code': 'someObject.voidMethod();',
                'mutated_code': '// mutation1'
            },
            {
                'line_number': 7, 
                'original_code': 'x > 0',
                'mutated_code': 'x >= 0'
            }
        ]
        
        success = mutation_applier.apply_multiple_mutations(sample_java_file, mutations)
        
        assert success is True
        
        # Verify both mutations were applied
        with open(sample_java_file, 'r') as f:
            content = f.read()
        
        assert "// mutation1" in content
        assert "return x >= 0;" in content