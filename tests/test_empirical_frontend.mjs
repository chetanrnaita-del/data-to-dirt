// Empirical test of student.js error handling, audio alerts, and DOM updates
import fs from 'fs';
import path from 'path';
import assert from 'assert';

const studentJsCode = fs.readFileSync('src/ui/js/views/student.js', 'utf8');

function createMockElement(id) {
  return {
    id,
    style: {},
    innerHTML: '',
    value: '',
    checked: false,
    disabled: false,
    textContent: '',
    onclick: null,
    querySelector: () => null,
    querySelectorAll: () => [],
    classList: {
      add: () => {},
      remove: () => {}
    }
  };
}

function runEmpiricalFrontendSuite() {
  const elements = {};
  function getElement(id) {
    if (!elements[id]) {
      elements[id] = createMockElement(id);
    }
    return elements[id];
  }

  const audioCalls = {
    playGamingBuzzer: 0,
    playCoinDing: 0,
    playBlip: 0,
    playDeletionPoof: 0,
  };

  const mockWindow = {
    RetroAudio: {
      playGamingBuzzer: () => { audioCalls.playGamingBuzzer++; },
      playCoinDing: () => { audioCalls.playCoinDing++; },
      playBlip: () => { audioCalls.playBlip++; },
      playDeletionPoof: () => { audioCalls.playDeletionPoof++; },
    },
    document: {
      getElementById: (id) => getElement(id),
      body: {
        classList: { add: () => {}, remove: () => {} }
      }
    },
    innerWidth: 1024,
    innerHeight: 768,
    fetch: null,
  };

  // Run script in mock environment
  const fn = new Function('window', 'document', 'fetch', studentJsCode);
  fn(mockWindow, mockWindow.document, (...args) => mockWindow.fetch(...args));

  const view = mockWindow.StudentView;
  assert(view, "StudentView must be instantiated on window");

  console.log("✔ StudentDashboardView loaded successfully");

  async function testBackendErrorHttp400() {
    // Reset audio and elements
    audioCalls.playGamingBuzzer = 0;
    audioCalls.playCoinDing = 0;
    getElement("scanner-status-banner").innerHTML = "";
    getElement("btn-revoke-scan").style.display = "block";
    getElement("scanned-files-container").innerHTML = "";

    mockWindow.fetch = async () => ({
      ok: false,
      status: 400,
      json: async () => ({
        status: "error",
        error: "Permission denied accessing '/root/secret': [Errno 13] Permission denied",
        folder: "/root/secret",
        files_found: 0,
        files: []
      })
    });

    await view.executeScan("/root/secret", true);

    const banner = getElement("scanner-status-banner");
    const btnRevoke = getElement("btn-revoke-scan");
    const container = getElement("scanned-files-container");

    assert.strictEqual(banner.style.borderColor, "var(--c-danger-red)", "Banner border should be danger red");
    assert.strictEqual(banner.style.backgroundColor, "rgba(168, 36, 36, 0.15)", "Banner bg should be danger tinted");
    assert(banner.innerHTML.includes("❌ Scan Error: Permission denied"), "Banner must show Scan Error text");
    assert.strictEqual(btnRevoke.style.display, "none", "Revoke button must be hidden on error");
    assert.strictEqual(audioCalls.playGamingBuzzer, 1, "Must play gaming buzzer on error");
    assert.strictEqual(audioCalls.playCoinDing, 0, "Must NOT play coin ding on error");
    assert(container.innerHTML.includes("Directory Access / Scan Failed"), "Container must render error card");
    assert(container.innerHTML.includes("Permission denied"), "Container must include error message");
    assert.strictEqual(view.scannedFiles.length, 0, "scannedFiles must be empty");

    console.log("✔ Test Backend Error HTTP 400 passed");
  }

  async function testBackendErrorHttp200WithErrorStatus() {
    audioCalls.playGamingBuzzer = 0;
    audioCalls.playCoinDing = 0;

    mockWindow.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: "error",
        error: "Custom directory error occurred"
      })
    });

    await view.executeScan("/some/folder", true);

    const banner = getElement("scanner-status-banner");
    assert(banner.innerHTML.includes("❌ Scan Error: Custom directory error occurred"));
    assert.strictEqual(getElement("btn-revoke-scan").style.display, "none");
    assert.strictEqual(audioCalls.playGamingBuzzer, 1);
    assert.strictEqual(audioCalls.playCoinDing, 0);

    console.log("✔ Test Backend Error status: 'error' with HTTP 200 passed");
  }

  async function testNetworkException() {
    audioCalls.playGamingBuzzer = 0;
    audioCalls.playCoinDing = 0;

    mockWindow.fetch = async () => {
      throw new Error("Failed to fetch: Connection refused");
    };

    await view.executeScan("/some/folder", true);

    const banner = getElement("scanner-status-banner");
    assert(banner.innerHTML.includes("❌ Scan Error: Failed to fetch: Connection refused"));
    assert.strictEqual(getElement("btn-revoke-scan").style.display, "none");
    assert.strictEqual(audioCalls.playGamingBuzzer, 1);
    assert.strictEqual(audioCalls.playCoinDing, 0);

    console.log("✔ Test Network Exception passed");
  }

  async function testHttp500NonJson() {
    audioCalls.playGamingBuzzer = 0;
    audioCalls.playCoinDing = 0;

    mockWindow.fetch = async () => ({
      ok: false,
      status: 500,
      json: async () => { throw new Error("Unexpected token < in JSON"); }
    });

    await view.executeScan("/some/folder", true);

    const banner = getElement("scanner-status-banner");
    assert(banner.innerHTML.includes("HTTP 500: Scan failed"));
    assert.strictEqual(getElement("btn-revoke-scan").style.display, "none");
    assert.strictEqual(audioCalls.playGamingBuzzer, 1);
    assert.strictEqual(audioCalls.playCoinDing, 0);

    console.log("✔ Test HTTP 500 non-JSON error passed");
  }

  async function testSuccessScanRecovery() {
    audioCalls.playGamingBuzzer = 0;
    audioCalls.playCoinDing = 0;

    mockWindow.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: "completed",
        folder: "/Users/student/Desktop",
        files_found: 2,
        files: [
          {
            file_id: "f_01",
            file_name: "test.tmp",
            size_formatted: "10 MB",
            age_days: 200,
            category: "transient_trash",
            dark_data_tag: "Temporary cache/artifact",
            is_confidential: false
          },
          {
            file_id: "f_02",
            file_name: "secret.env",
            size_formatted: "1 KB",
            age_days: 10,
            category: "normal",
            dark_data_tag: "Normal",
            is_confidential: true
          }
        ]
      })
    });

    await view.executeScan("/Users/student/Desktop", true);

    const banner = getElement("scanner-status-banner");
    const btnRevoke = getElement("btn-revoke-scan");
    const container = getElement("scanned-files-container");

    assert.strictEqual(banner.style.borderColor, "", "Banner border should be reset on success");
    assert.strictEqual(banner.style.backgroundColor, "", "Banner bg should be reset on success");
    assert(banner.innerHTML.includes("Device Storage Scanned"), "Banner must show Device Storage Scanned");
    assert(banner.innerHTML.includes("2 files analyzed"), "Banner must show files analyzed");
    assert.strictEqual(btnRevoke.style.display, "inline-flex", "Revoke button must be shown on success");
    assert.strictEqual(audioCalls.playCoinDing, 1, "Must play coin ding on success");
    assert.strictEqual(audioCalls.playGamingBuzzer, 0, "Must NOT play buzzer on success");

    assert(container.innerHTML.includes("test.tmp"), "Container must render scanned files");
    assert(container.innerHTML.includes("secret.env"), "Container must render confidential file");
    assert(container.innerHTML.includes("🔒 [CONFIDENTIAL]"), "Must tag confidential file");

    console.log("✔ Test Success Scan Recovery passed");
  }

  async function testRevokeFolderAccess() {
    audioCalls.playBlip = 0;

    mockWindow.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: "revoked",
        files_purged: 2
      })
    });

    await view.revokeFolderAccess();

    const banner = getElement("scanner-status-banner");
    const btnRevoke = getElement("btn-revoke-scan");
    const container = getElement("scanned-files-container");

    assert(banner.innerHTML.includes("Blind State"), "Banner must show Blind State after revoke");
    assert.strictEqual(btnRevoke.style.display, "none", "Revoke button must be hidden");
    assert.strictEqual(audioCalls.playBlip, 1, "Must play blip sound on revoke");
    assert(container.innerHTML.includes("Ready to Clean Real Data") || container.innerHTML.includes("No active files in memory"), "Container must show blind state");
    assert.strictEqual(view.scannedFiles.length, 0, "scannedFiles must be purged");

    console.log("✔ Test Revoke Folder Access passed");
  }

  return (async () => {
    await testBackendErrorHttp400();
    await testBackendErrorHttp200WithErrorStatus();
    await testNetworkException();
    await testHttp500NonJson();
    await testSuccessScanRecovery();
    await testRevokeFolderAccess();
    console.log("\nALL FRONTEND EMPIRICAL TESTS PASSED!");
  })();
}

runEmpiricalFrontendSuite().catch(err => {
  console.error("Test failure:", err);
  process.exit(1);
});
