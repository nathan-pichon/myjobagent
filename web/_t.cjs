const {JSDOM}=require("jsdom"); const fs=require("fs");
(async()=>{
let state={running:true,progress:{phase:"france-travail · 2 matches",steps:4,urls_seen:9,matches:2,new:1,last_match:{title:"Tech Lead"}},last_run:null,jobs_count:1,matches_count:1,last_added:1000};
// inject fetch via beforeParse so it exists when inline scripts run
const dom=new JSDOM(fs.readFileSync("/tmp/dlive.html","utf8"),{
  runScripts:"dangerously",pretendToBeVisual:true,url:"http://127.0.0.1:4321/",
  beforeParse(window){
    window.fetch=(url,opts)=>{
      if(url==="/api/state") return Promise.resolve({json:()=>Promise.resolve(state)});
      return Promise.resolve({json:()=>Promise.resolve({ok:true})});
    };
  }
});
const {window}=dom; const doc=window.document;
await new Promise(z=>setTimeout(z,80));
const r={};
r.runTopVisible=!doc.getElementById("run-now-top").hidden;
r.bannerShownDuringHunt=!doc.getElementById("live-banner").hidden;
r.phaseText=doc.getElementById("live-phase").textContent;
r.countsText=doc.getElementById("live-counts").textContent;
// hunt finishes + new job landed
state={running:false,progress:null,last_run:{matches:3},jobs_count:2,matches_count:2,last_added:2000};
await new Promise(z=>setTimeout(z,2700));
r.bannerHiddenAfter=doc.getElementById("live-banner").hidden;
r.toastShown=!doc.getElementById("new-jobs-toast").hidden;
console.log(JSON.stringify(r,null,2));
})();
