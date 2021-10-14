import requests
import sys
from pathlib import Path


def fetch_tools(conf, quite=False):
    if 'tools' in conf:
        for key in conf['tools'].keys():
            tool_path = Path(conf['tools'][key]['path'])
            if not tool_path.exists() and 'url' in conf['tools'][key]:
                url = conf['tools'][key]['url']
                if not tool_path.parent.exists():
                    tool_path.parent.mkdir(exist_ok=True, parents=True)
                if not quite:
                    print("Fetching tool %s from %s" % (str(tool_path), url))
                link = url
                file_name = tool_path

                with open(file_name, "wb") as f:
                    if not quite:
                        print("Downloading %s" % file_name)
                    response = requests.get(link, stream=True)
                    total_length = response.headers.get('content-length')

                    if total_length is None:  # no content length header
                        f.write(response.content)
                    else:
                        dl = 0
                        total_length = int(total_length)
                        for data in response.iter_content(chunk_size=4096):
                            dl += len(data)
                            f.write(data)
                            done = int(50 * dl / total_length)
                            if not quite:
                                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                                sys.stdout.flush()
