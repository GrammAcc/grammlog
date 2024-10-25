from pathlib import Path

import grammlog

readme_heading = """# grammlog\n\nGrammAcc's structured logging.

[API Docs](https://grammacc.github.io/grammlog)
"""

doc = grammlog.__doc__
new_readme = "\n".join([readme_heading, doc])

Path("README.md").write_text(new_readme)
