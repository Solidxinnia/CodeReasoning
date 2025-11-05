import shutil
import re
from pathlib import Path
import subprocess
import json
import time
import random
import csv
from datetime import datetime

# --- Configuration ---
DEFECTS4J_EXECUTABLE = "defects4j"

BUGS_TO_PROCESS = [ ("Chart" ,"3")]
'''("Math" ,"2"),
("Math" ,"3"),
("Math" ,"4"),
("Math","5"),
("Math","6"),
("Math","7"),
("Math","8"),
("Math","9"),
("Math","10"),
("Math","11"),
("Math","12"),
("Math","13"),
("Math","14"),
("Math","15"),
("Math","16"),
("Math","17"),
("Math","18"),
("Math","19"),
("Math","20"),
("Math","21"),
("Math","22"),
("Math","23"),
("Math","24"),
("Math","25"),
("Math","26"),
("Math","27"),
("Math","28"),
("Math","29"),
("Math","30"),
("Math","31"),
("Math","32"),
("Math","33"),
("Math","34"),
("Math","35"),
("Math","36"),
("Math","37"),
("Math","38"),
("Math","39"),
("Math","40"),
("Math","41"),
("Math","42"),
("Math","43"),
("Math","44"),
("Math","45"),
("Math","46"),
("Math","47"),
("Math","48"),
("Math","49"),
("Math","50"),
("Math","51"),
("Math","52"),
("Math","53"),
("Math","54"),
("Math","55"),
("Math","56"),
("Math","57"),
("Math","58"),
("Math","59"),
("Math","60"),
("Math","61"),
("Math","62"),
("Math","63"),
("Math","64"),
("Math","65"),
("Math","66"),
("Math","67"),
("Math","68"),
("Math","69"),
("Math","70"),
("Math","71"),
("Math","72"),
("Math","73"),
("Math","74"),
("Math","75"),
("Math","76"),
("Math","77"),
("Math","78"),
("Math","79"),
("Math","80"),
("Math","81"),
("Math","82"),
("Math","83"),
("Math","84"),
("Math","85"),
("Math","86"),
("Math","87"),
("Math","88"),
("Math","89"),
("Math","90"),
("Math","91"),
("Math","92"),
("Math","93"),
("Math","94"),
("Math","95"),
("Math","96"),
("Math","97"),
("Math","98"),
("Math","99"),
("Math","100"),
("Math","101"),
("Math","102"),
("Math","103"),
("Math","104"),
("Math","105"),
("Math","106")'''

BASE_CHECKOUT_DIR = Path("/tmp/mutated_codes")

def run_command(command, working_dir, step_name="Command"):
    """Runs a shell command and returns True on success, False on failure."""
    print(f"    Running: {' '.join(command)}")
    result = subprocess.run(
        command, check=True, capture_output=True, text=True, cwd=working_dir
    )
    return result

def get_source_directories(work_dir):
    """Get all possible source directories from Defects4J - handle different project structures"""
    print("   Finding source directories...")
    
    source_dirs = []
    
    # Common source directory patterns in Defects4J projects
    possible_dirs = [
        work_dir / "src",
        work_dir / "src/main/java",  # Maven structure
        work_dir / "src/java",
        work_dir / "source",
        work_dir / "Source",
    ]
    
    # Also try to get from Defects4J export
    try:
        proc = subprocess.run(
            [DEFECTS4J_EXECUTABLE, "export", "-p", "dir.src.classes"],
            capture_output=True, text=True, check=True, cwd=work_dir
        )
        def_src_dir = work_dir / proc.stdout.strip()
        if def_src_dir.exists():
            source_dirs.append(def_src_dir)
            print(f"   Defects4J source dir: {def_src_dir}")
    except:
        pass
    
    # Check all possible directories
    for dir_path in possible_dirs:
        if dir_path.exists():
            source_dirs.append(dir_path)
            print(f"   Found source dir: {dir_path}")
    
    # Search for Java files to find source directories
    java_dirs = set()
    for java_file in work_dir.rglob("*.java"):
        java_dirs.add(java_file.parent)
    
    # Add directories that contain Java files and look like source directories
    for java_dir in java_dirs:
        if any(pattern in str(java_dir) for pattern in ['src', 'java', 'source']):
            if java_dir not in source_dirs:
                source_dirs.append(java_dir)
    
    print(f"   Total source directories found: {len(source_dirs)}")
    return source_dirs

def find_mutants_log(work_dir):
    """Find the mutants.log file"""
    print("   Searching for mutants.log...")
    
    # Search recursively
    log_files = list(work_dir.rglob("mutants.log"))
    if log_files:
        print(f"   Found mutants.log: {log_files[0]}")
        return log_files[0]
    
    print("   No mutants.log file found")
    return None

def parse_mutants_log_line_corrected(line):
    """
    Corrected parsing of mutants.log lines using the specified parsing logic
    Format: ID:MUTATOR:SIG_ORIG:SIG_MUT:CLASS@METHOD:LINE:CODE_ORIG |==> CODE_MUT
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    try:
        # Split by colon to get main parts
        parts = line.split(':')
        if len(parts) < 8:
            return None
        
        mutant_id = parts[0]
        mutator = parts[1]
        original_sig = parts[2]
        mutated_sig = parts[3]
        class_method = parts[4]
        line_num = parts[5]  
        garbage = parts[6]
        code = parts[7]
        
        # Extract code change
        if '|==>' in code:
            original_code, mutated_code = code.split('|==>', 1)
            original_code = original_code.strip()
            mutated_code = mutated_code.strip()
            
            # Handle <NO-OP> mutations - keep operation empty
            if mutated_code == '<NO-OP>':
                mutated_code = ""
        else:
            original_code = code.strip()
            mutated_code = ""
        
        # Extract class name from class@method
        if '@' in class_method:
            class_name = class_method.split('@')[0]
            method_name = class_method.split('@')[1]
        else:
            class_name = class_method
            method_name = ""
        
        # Convert line number to integer
        try:
            line_number = int(line_num)
        except ValueError:
            return None
        
        mutant_info = {
            'mutant_id': mutant_id,
            'mutator': mutator,
            'original_signature': original_sig,
            'mutated_signature': mutated_sig,
            'class_name': class_name,
            'method_name': method_name,
            'line_number': line_number,
            'original_code': original_code,
            'mutated_code': mutated_code,
            'raw_line': line
        }
        
        return mutant_info
        
    except Exception as e:
        return None

def find_java_file_by_class(class_name, source_dirs):
    """Find Java file by class name across all source directories"""
    # Convert class name to file path
    file_rel_path = class_name.replace('.', '/') + '.java'
    
    for src_dir in source_dirs:
        # Try direct path
        direct_path = src_dir / file_rel_path
        if direct_path.exists():
            return direct_path
        
        # Try with src/main/java prefix (common in Maven projects)
        maven_path = src_dir / "src/main/java" / file_rel_path
        if maven_path.exists():
            return maven_path
        
        # Try with src/java prefix
        src_java_path = src_dir / "src/java" / file_rel_path
        if src_java_path.exists():
            return src_java_path
    
    # Search recursively for the file
    for src_dir in source_dirs:
        search_pattern = f"**/{class_name.split('.')[-1]}.java"
        matches = list(src_dir.rglob(search_pattern))
        if matches:
            return matches[0]
    
    return None

def apply_mutation_to_file(source_file, line_number, original_code, mutated_code):
    """Apply mutation to a specific file"""
    try:
        if not source_file.exists():
            return False
        
        # Read the file
        with open(source_file, 'r') as f:
            lines = f.readlines()
        
        # Check line number
        if line_number < 1 or line_number > len(lines):
            return False
        
        target_line_index = line_number - 1
        original_line = lines[target_line_index]
        
        # Try exact replacement
        if original_code in original_line:
            mutated_line = original_line.replace(original_code, mutated_code)
            lines[target_line_index] = mutated_line
        
        # Try with stripped whitespace
        elif original_code.strip() in original_line.strip():
            # Find the exact position and preserve formatting
            stripped_original = original_code.strip()
            stripped_line = original_line.strip()
            
            if stripped_original in stripped_line:
                start_idx = original_line.find(stripped_original)
                if start_idx != -1:
                    end_idx = start_idx + len(stripped_original)
                    before = original_line[:start_idx]
                    after = original_line[end_idx:]
                    mutated_line = before + mutated_code + after
                    lines[target_line_index] = mutated_line
        else:
            return False
        
        # Write the modified content back
        with open(source_file, 'w') as f:
            f.writelines(lines)
        
        return True
        
    except Exception as e:
        return False

def create_full_project_copy(original_work_dir, copy_dir):
    """Create a full copy of the project"""
    print(f"   Creating full project copy: {copy_dir.name}")
    
    if copy_dir.exists():
        shutil.rmtree(copy_dir)
    
    # Copy the entire project
    shutil.copytree(original_work_dir, copy_dir)
    print(f"   Successfully created full project copy")
    return True

def parse_failing_tests_file(mutant_dir):
    """Parse failing tests from the failing_tests file - start from '----' until 'junit' or 'java'"""
    failing_tests_file = mutant_dir / "failing_tests"
    failed_tests = []
    
    if failing_tests_file.exists():
        try:
            with open(failing_tests_file, 'r', encoding='utf-8') as infile:
                for line in infile:
                # Strip leading/trailing whitespace from the line
                    stripped_line = line.strip()
                
                # Check if the line starts with '--- '
                    if stripped_line.startswith('--- '):
                    # Extract the part after '--- '
                        test_name = stripped_line[4:].strip()
                    
                    # Ensure it's a valid test name line (not just '---')
                        if test_name:
                            failed_tests.append(test_name)
        except FileNotFoundError:
            print(f"Error: The file '{failing_tests_file}' was not found.")
            return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    return failed_tests

def read_all_tests_file(mutant_dir):
    """Read all tests from all_tests.txt file"""
    all_tests_file = mutant_dir / "all_tests"
    all_tests = []
    
    if all_tests_file.exists():
        try:
            with open(all_tests_file, 'r') as f:
                all_tests = [line.strip() for line in f if line.strip()]
            print(f"   Found {len(all_tests)} total tests in all_tests")
        except Exception as e:
            print(f"   Error reading all_tests: {e}")
    
    return all_tests

def run_coverage_and_tests(mutant_dir, project_id, bug_id):
    """Run coverage and tests on a mutant, return failed tests and coverage info"""
    print(f"   Running coverage and tests for mutant...")
    
    coverage_result = {
        'coverage_success': False,
        'failed_tests': [],
        'all_tests': [],
        'total_tests': 0,
        'failed_count': 0,
        'coverage_output': ''
    }
    
    try:
        # First compile the mutant
        compile_result = run_command([DEFECTS4J_EXECUTABLE, "compile"], mutant_dir, "Compile mutant")
        if not compile_result:
            print("   Failed to compile mutant")
            return coverage_result
        
        # Run coverage
        print("   Running defects4j coverage...")
        coverage_process = subprocess.run(
            [DEFECTS4J_EXECUTABLE, "coverage", "-r"],
            capture_output=True, 
            text=True, 
            cwd=mutant_dir,
            timeout=600  # 10 minute timeout
        )
        
        coverage_result['coverage_output'] = coverage_process.stdout + coverage_process.stderr
        coverage_result['coverage_success'] = (coverage_process.returncode == 0)
        
        # Parse failing tests from file using the new parsing method
        failed_tests = parse_failing_tests_file(mutant_dir)
        coverage_result['failed_tests'] = failed_tests
        coverage_result['failed_count'] = len(failed_tests)
        
        # Read all tests from all_tests.txt
        all_tests = read_all_tests_file(mutant_dir)
        coverage_result['all_tests'] = all_tests
        coverage_result['total_tests'] = len(all_tests)
        
        print(f"   Coverage completed - {coverage_result['failed_count']}/{coverage_result['total_tests']} tests failed")
        
    except subprocess.TimeoutExpired:
        print("   Coverage command timed out after 10 minutes")
        coverage_result['coverage_output'] = "TIMEOUT: Coverage command took too long"
    except Exception as e:
        print(f"   Error running coverage: {e}")
        coverage_result['coverage_output'] = f"ERROR: {str(e)}"
    
    return coverage_result

def create_single_mutant(original_work_dir, mutant_dir, mutation_info, project_id, bug_id):
    """Create a single mutant by applying one mutation to a project copy and run coverage"""
    print(f"   Creating mutant {mutant_dir.name}...")
    
    # Create full project copy
    if not create_full_project_copy(original_work_dir, mutant_dir):
        return None
    
    # Get source directories from the project copy
    source_dirs = get_source_directories(mutant_dir)
    if not source_dirs:
        print(f"   No source directories found in {mutant_dir}")
        return None
    
    # Find the target file
    class_name = mutation_info['class_name']
    target_file = find_java_file_by_class(class_name, source_dirs)
    
    if not target_file:
        print(f"   Could not find Java file for class: {class_name}")
        return None
    
    # Apply the single mutation
    success = apply_mutation_to_file(
        target_file,
        mutation_info['line_number'],
        mutation_info['original_code'],
        mutation_info['mutated_code']
    )
    
    if success:
        # Run coverage and tests on the mutant
        coverage_result = run_coverage_and_tests(mutant_dir, project_id, bug_id)
        
        result_info = {
            'mutant_id': mutation_info['mutant_id'],
            'mutant_directory': str(mutant_dir),
            'mutator': mutation_info['mutator'],
            'class_name': mutation_info['class_name'],
            'line_number': mutation_info['line_number'],
            'target_file': str(target_file.relative_to(mutant_dir)),
            'total_tests_count': coverage_result['total_tests'],
            'failed_test_count': coverage_result['failed_count'],
            'failed_tests': coverage_result['failed_tests'],
            'all_tests': coverage_result['all_tests'],  # Store all tests for CSV
            'coverage_success': coverage_result['coverage_success'],
            'coverage_output_file': str(mutant_dir / "coverage_output.log")
        }
        
        # Save coverage output to file
        with open(mutant_dir / "coverage_output.log", 'w') as f:
            f.write(coverage_result['coverage_output'])
        
        print(f"   Successfully created mutant {mutant_dir.name}")
        return result_info
    else:
        print(f"   Failed to apply mutation to {mutant_dir.name}")
        # Clean up failed mutant
        if mutant_dir.exists():
            shutil.rmtree(mutant_dir)
        return None

def parse_all_mutations(log_file):
    """Parse all mutations from mutants.log"""
    print(f"   Parsing all mutations from {log_file.name}...")
    
    all_mutations = []
    prevline = -1
    prevmut = -1
    try:
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip() and not line.strip().startswith('#'):
                    mutation_info = parse_mutants_log_line_corrected(line)
                    if mutation_info and mutation_info['line_number'] == prevline and mutation_info['mutator'] == prevmut:
                        prevline = mutation_info['line_number']
                        prevmut = mutation_info['mutator']
                        continue
                    prevline = mutation_info['line_number']
                    prevmut = mutation_info['mutator']
                    if mutation_info:
                        all_mutations.append(mutation_info)
    
    except Exception as e:
        print(f"   Error parsing log file: {e}")
    
    print(f"   Parsed {len(all_mutations)} total mutations")
    return all_mutations

def create_single_mutants(original_work_dir, mutants_output_dir, all_mutations, num_mutants, project_id, bug_id):
    """Create multiple mutants, each with a single mutation, and run coverage"""
    print(f"   Creating {num_mutants} mutants (one mutation per mutant)...")
    
    if num_mutants == 'all':
        num_mutants = len(all_mutations)
        print(f"   Creating ALL {num_mutants} mutants from mutants.log")
    else:
        # Limit to available mutations
        num_mutants = min(num_mutants, len(all_mutations))
        print(f"   Creating {num_mutants} mutants from {len(all_mutations)} available mutations")
    
    successful_mutants = []
    failed_mutations = []
    
    for i in range(num_mutants):
        mutation_info = all_mutations[i]
        print(f"  --- Creating Mutant {i+1}/{num_mutants} (ID: {mutation_info['mutant_id']}) ---")
        
        # Create mutant directory name
        mutant_dir = mutants_output_dir / f"mutated_proj_copy_{mutation_info['mutant_id']}"
        
        # Create single mutant and run coverage
        mutant_result = create_single_mutant(
            original_work_dir, 
            mutant_dir, 
            mutation_info,
            project_id,
            bug_id
        )
        
        if mutant_result:
            successful_mutants.append(mutant_result)
            print(f"   Successfully created mutant {mutation_info['mutant_id']}")
        else:
            failed_mutations.append(mutation_info)
            print(f"   Failed to create mutant {mutation_info['mutant_id']}")
        
        print()
    
    return successful_mutants, failed_mutations

def create_coverage_csv(successful_mutants, csv_file_path):
    """Create a CSV file with coverage and test failure information"""
    print(f"   Creating coverage CSV file: {csv_file_path}")
    
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = [
            'mutant_id',
            'mutator',
            'class_name', 
            'line_number',
            'target_file',
            'total_tests_count',
            'failed_test_count',
            'failed_tests',
            'all_tests'  # 9th column with all test names from all_tests.txt
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for mutant in successful_mutants:
            # Prepare row data
            row_data = {
                'mutant_id': mutant['mutant_id'],
                'mutator': mutant['mutator'],
                'class_name': mutant['class_name'],
                'line_number': mutant['line_number'],
                'target_file': mutant['target_file'],
                'total_tests_count': mutant['total_tests_count'],
                'failed_test_count': mutant['failed_test_count'],
                'failed_tests': '; '.join(mutant['failed_tests']),  # Join failed tests with semicolons
                'all_tests': '; '.join(mutant['all_tests'])  # Join all tests with semicolons
            }
            
            writer.writerow(row_data)
    
    print(f"   CSV file created with {len(successful_mutants)} entries")

def run_mutation_testing(work_dir):
    """Run Defects4J mutation testing"""
    print("   Running mutation testing...")
    
    try:
        result = subprocess.run(
            [DEFECTS4J_EXECUTABLE, "mutation"],
            capture_output=True, 
            text=True, 
            cwd=work_dir,
            timeout=300
        )
        
        print(f"   Mutation testing completed (return code: {result.returncode})")
        return True
        
    except Exception as e:
        print(f"   Mutation testing error: {e}")
        return False

def process_bug_for_mutants(project_id, bug_id):
    """Process a bug to create multiple mutants with single mutations and run coverage"""
    work_dir = BASE_CHECKOUT_DIR / f"{project_id}_{bug_id}f"
    mutants_output_dir = BASE_CHECKOUT_DIR / f"mutants_{project_id}_{bug_id}"
    
    print(f"This is the code for one mutant per project copy")
    
    # Clean up
    if work_dir.exists():
        shutil.rmtree(work_dir)
    if mutants_output_dir.exists():
        shutil.rmtree(mutants_output_dir)
    
    mutants_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Checkout and compile
    print("\n1.  Checking out and compiling project...")
    checkout_cmd = [DEFECTS4J_EXECUTABLE, "checkout", "-p", project_id, "-v", f"{bug_id}f", "-w", str(work_dir)]
    if not run_command(checkout_cmd, BASE_CHECKOUT_DIR, "Checkout"):
        return False
    
    if not run_command([DEFECTS4J_EXECUTABLE, "compile"], work_dir, "Compile"):
        return False
    
    # Step 2: Find source directories
    print("\n2.  Finding source directories...")
    source_dirs = get_source_directories(work_dir)
    if not source_dirs:
        print("   No source directories found")
        return False
    
    # Step 3: Run mutation testing
    print("\n3.  Running mutation testing...")
    run_mutation_testing(work_dir)
    
    # Step 4: Find mutants.log
    print("\n4.  Finding mutants.log...")
    log_file = find_mutants_log(work_dir)
    if not log_file:
        print("   No mutants.log found")
        return False
    
    # Step 5: Parse all mutations
    print("\n5.  Parsing all mutations...")
    all_mutations = parse_all_mutations(log_file)
    if not all_mutations:
        print("   No mutations could be parsed")
        return False
    
    #print("how many mutants do you want to create?")
    num_mutants = 2
    
    # Step 6: Create single mutants (one mutation per mutant) and run coverage
    print("\n6.  Creating single mutants and running coverage...")
    successful_mutants, failed_mutations = create_single_mutants(
        work_dir,
        mutants_output_dir, 
        all_mutations, 
        num_mutants,
        project_id,
        bug_id
    )
    
    if not successful_mutants:
        print("   No mutants were successfully created")
        return False
    
    # Step 7: Create coverage CSV file
    print("\n7.  Creating coverage CSV file...")
    csv_file_path = mutants_output_dir / "coverage_results.csv"
    create_coverage_csv(successful_mutants, csv_file_path)
    
    # Step 8: Create comprehensive summary
    print("\n8.  Creating summary...")
    
    # Calculate coverage statistics
    total_coverage_success = sum(1 for m in successful_mutants if m['coverage_success'])
    total_failed_tests = sum(m['failed_test_count'] for m in successful_mutants)
    mutants_with_failures = sum(1 for m in successful_mutants if m['failed_test_count'] > 0)
    
    summary = {
        'project': project_id,
        'bug_id': bug_id,
        'total_mutations_available': len(all_mutations),
        'total_mutants_created': len(successful_mutants),
        'total_mutants_failed': len(failed_mutations),
        'coverage_success_rate': f"{(total_coverage_success / len(successful_mutants) * 100):.1f}%",
        'total_failed_tests_across_mutants': total_failed_tests,
        'mutants_with_test_failures': mutants_with_failures,
        'success_rate': f"{(len(successful_mutants) / num_mutants * 100):.1f}%",
        'source_directories': [str(d) for d in source_dirs],
        'coverage_csv_file': str(csv_file_path),
        'timestamp': datetime.now().isoformat()
    }
    
    summary_file = mutants_output_dir / "single_mutants_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Save original log and all mutations for reference
    shutil.copy2(log_file, mutants_output_dir / "original_mutants.log")
    
    # Save the list of all parsed mutations
    with open(mutants_output_dir / "all_parsed_mutations.json", 'w') as f:
        json.dump(all_mutations, f, indent=2)
    
    print(f"\n FINAL RESULTS:")
    print(f"  - Total mutations available: {len(all_mutations)}")
    print(f"  - Mutants created: {len(successful_mutants)}")
    print(f"  - Mutants failed: {len(failed_mutations)}")
    print(f"  - Coverage success rate: {(total_coverage_success / len(successful_mutants) * 100):.1f}%")
    print(f"  - Total test failures across mutants: {total_failed_tests}")
    print(f"  - Mutants with test failures: {mutants_with_failures}")
    
    success_rate = (len(successful_mutants) / num_mutants * 100)
    print(f"  - Overall success rate: {success_rate:.1f}%")
    print(f"  - Coverage CSV file: {csv_file_path}")
    
    if successful_mutants:
        print(f"   SUCCESS - All mutants saved in: {mutants_output_dir}")
        
        # Show first 3 successful mutants as sample
        print(f"\n SAMPLE SUCCESSFUL MUTANTS:")
        for mutant in successful_mutants[:3]:
            print(f"  - Mutant {mutant['mutant_id']}: {mutant['mutator']} at line {mutant['line_number']}")
            print(f"    File: {mutant['target_file']}")
            print(f"    Failed tests: {mutant['failed_test_count']}/{mutant['total_tests_count']}")
            if mutant['failed_tests']:
                print(f"    Test failures: {', '.join(mutant['failed_tests'][:3])}{'...' if len(mutant['failed_tests']) > 3 else ''}")
        
        if len(successful_mutants) > 3:
            print(f"  ... and {len(successful_mutants) - 3} more mutants")
        
        return True
    else:
        print(f"   FAILED - No mutants were created")
        return False

def main():
    """Main function"""
    print(f" DEFECTS4J SINGLE MUTANT GENERATOR WITH COVERAGE")
    print(f"Creating mutants with one mutation per project copy and running coverage")
    print("="*80)
    
    BASE_CHECKOUT_DIR.mkdir(exist_ok=True)
    
    for project, bug in BUGS_TO_PROCESS:
        print(f"\n{'='*80}")
        print(f" PROCESSING: {project}-{bug}")
        print(f"{'='*80}")
        
        success = process_bug_for_mutants(project, bug)
        status = " SUCCESS" if success else " FAILED"
        print(f"{status}: {project}-{bug}")

if __name__ == "__main__":
    main()