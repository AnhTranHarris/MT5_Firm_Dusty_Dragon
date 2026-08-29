(() => {
  "use strict";

  const command=document.querySelector("#command");
  const nav=document.querySelector(".workspace-nav");
  if(!command||!nav)return;

  const authority=command.querySelector(".authority-zone");
  const research=command.querySelector("#researchDelta")?.closest("article.panel");
  const rejected=command.querySelector("#rejectedSummary")?.closest("article.panel");
  const rightStack=command.querySelector(".right-stack");

  /* Command Authority is an application-level action surface, not a telemetry
     panel. Promote its two bounded mock commands beside SYSTEM and retire the
     panel so the right rail can carry information instead of controls. */
  if(authority){
    const actionGroup=document.createElement("div");
    actionGroup.className="nav-command-authority";
    actionGroup.setAttribute("aria-label","Command authority");
    authority.querySelectorAll("button[data-command]").forEach(source=>{
      const button=source.cloneNode(true);
      button.classList.add("nav-authority-button");
      if(source.classList.contains("danger"))button.classList.add("danger");
      actionGroup.append(button);
    });
    nav.append(actionGroup);
    authority.remove();
  }

  /* Research Delta belongs with rejected-opportunity/research feedback. Moving
     the existing node preserves the original data binding and avoids duplicate
     presentation state. */
  if(research&&rejected&&rightStack){
    rejected.insertAdjacentElement("afterend",research);
    research.classList.add("research-delta-relocated");
  }

  window.DUSTY_COMMAND_LAYOUT=Object.freeze({version:"3.6",authorityLocation:"TOP_NAV_AFTER_SYSTEM",researchDeltaLocation:"RIGHT_RAIL_AFTER_REJECTED"});
})();