import subprocess
import tempfile
import os
import json
import resource
from typing import Any, Dict
from pathlib import Path
import shutil

class LanguageConfig:
    CONFIGS = {
        'python': {
            'file_extension': '.py',
            'compile_cmd': None,
            'run_cmd': ['python', '{file}'],
            'wrapper_code': '''
import json
import sys

def run_code(input_data):
{code}

if __name__ == "__main__":
    input_data = json.loads(sys.argv[1])
    result = run_code(input_data)
    print(json.dumps({{"result": result}}))
'''
        },
        'javascript': {
            'file_extension': '.js',
            'compile_cmd': None,
            'run_cmd': ['node', '{file}'],
            'wrapper_code': '''
function run_code(input_data) {
{code}
}

const input_data = JSON.parse(process.argv[2]);
const result = run_code(input_data);
console.log(JSON.stringify({result: result}));
'''
        },
        'java': {
            'file_extension': '.java',
            'compile_cmd': ['javac', '{file}'],
            'run_cmd': ['java', 'Solution'],
            'wrapper_code': '''
import com.google.gson.Gson;
import java.util.Map;

public class Solution {{
    public static Object runCode(Map<String, Object> inputData) {{
{code}
    }}
    
    public static void main(String[] args) {{
        Gson gson = new Gson();
        Map<String, Object> inputData = gson.fromJson(args[0], Map.class);
        Object result = runCode(inputData);
        System.out.println(gson.toJson(new ResultWrapper(result)));
    }}
    
    static class ResultWrapper {{
        public Object result;
        public ResultWrapper(Object result) {{
            this.result = result;
        }}
    }}
}}
'''
        },
        'cpp': {
            'file_extension': '.cpp',
            'compile_cmd': ['g++', '-std=c++17', '{file}', '-o', '{executable}'],
            'run_cmd': ['{executable}'],
            'wrapper_code': '''
#include <iostream>
#include <string>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

auto run_code(const json& input_data) {
{code}
}

int main(int argc, char* argv[]) {
    json input_data = json::parse(argv[1]);
    auto result = run_code(input_data);
    json output = {{"result", result}};
    std::cout << output.dump() << std::endl;
    return 0;
}
'''
        }
    }

class CodeExecutor:
    def __init__(self):
        self.timeout = 5  # Maximum execution time in seconds
        self.languages = LanguageConfig.CONFIGS

    def _create_temp_dir(self):
        return tempfile.mkdtemp()

    def _write_code_file(self, temp_dir: str, code: str, language: str) -> str:
        lang_config = self.languages[language]
        file_extension = lang_config['file_extension']
        wrapper_code = lang_config['wrapper_code']
        
        # Indent the code for the wrapper
        indented_code = '\n'.join('    ' + line for line in code.split('\n'))
        final_code = wrapper_code.format(code=indented_code)
        
        file_path = os.path.join(temp_dir, f'Solution{file_extension}')
        with open(file_path, 'w') as f:
            f.write(final_code)
        
        return file_path

    def _compile_code(self, file_path: str, language: str, temp_dir: str) -> tuple[bool, str]:
        lang_config = self.languages[language]
        compile_cmd = lang_config.get('compile_cmd')
        
        if compile_cmd is None:
            return True, ""
            
        executable = os.path.join(temp_dir, 'solution')
        try:
            cmd = [c.format(file=file_path, executable=executable) for c in compile_cmd]
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                return False, process.stderr
                
            return True, ""
        except Exception as e:
            return False, str(e)

    def execute_code(self, code: str, language: str, input_data: dict) -> dict:
        temp_dir = None
        try:
            temp_dir = self._create_temp_dir()
            file_path = self._write_code_file(temp_dir, code, language)
            
            # Set resource limits
            resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
            resource.setrlimit(resource.RLIMIT_AS, (50 * 1024 * 1024, 50 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_NOFILE, (10, 10))
            
            # Compile if needed
            success, error = self._compile_code(file_path, language, temp_dir)
            if not success:
                return {
                    'status': 'error',
                    'error': f'Compilation failed: {error}'
                }
            
            # Run the code
            lang_config = self.languages[language]
            run_cmd = [c.format(
                file=file_path,
                executable=os.path.join(temp_dir, 'solution')
            ) for c in lang_config['run_cmd']]
            
            process = subprocess.run(
                run_cmd + [json.dumps(input_data)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=temp_dir
            )
            
            if process.returncode == 0:
                try:
                    result = json.loads(process.stdout)['result']
                    return {
                        'status': 'success',
                        'result': result
                    }
                except json.JSONDecodeError:
                    return {
                        'status': 'error',
                        'error': 'Invalid output format'
                    }
            else:
                return {
                    'status': 'error',
                    'error': f'Execution failed: {process.stderr}'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'error': 'Execution timed out'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)