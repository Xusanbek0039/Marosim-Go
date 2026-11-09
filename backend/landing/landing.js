(() => {
  'use strict';
  const root = document.documentElement;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  document.getElementById('year').textContent = new Date().getFullYear();

  // Same cabinet paths in production and on the project's LAN ports.
  const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1' || /^\d{1,3}(\.\d{1,3}){3}$/.test(location.hostname);
  const cabinets = {user:['userlogin',3002],studio:['studio',8002],venue:['toyxona',3003]};
  document.querySelectorAll('[data-cabinet]').forEach(link => {
    const [subdomain,port] = cabinets[link.dataset.cabinet], path = link.dataset.path || '/';
    const target = local ? new URL(location.origin) : new URL(`https://${subdomain}.marosimgo.uz`);
    if (local) target.port = String(port);
    target.pathname = path; link.href = target.href;
  });

  const theme = document.getElementById('theme-btn');
  function syncTheme() {
    const dark = root.dataset.theme !== 'light';
    root.dataset.theme = dark ? 'dark' : 'light';
    theme.setAttribute('aria-label',dark ? 'Yorug‘ rejimga o‘tish' : 'Qorong‘i rejimga o‘tish');
    document.getElementById('theme-color').content = dark ? '#101211' : '#f1f3eb';
    document.dispatchEvent(new Event('mg:theme'));
  }
  theme.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
    try { localStorage.setItem('mg-theme',root.dataset.theme); } catch {}
    syncTheme();
  }); syncTheme();

  const menuButton = document.getElementById('menu-button'), menu = document.getElementById('mobile-menu');
  function closeMenu(returnFocus=false) { menu.hidden=true;menuButton.setAttribute('aria-expanded','false');menuButton.setAttribute('aria-label','Menyuni ochish');if(returnFocus)menuButton.focus(); }
  menuButton.addEventListener('click', () => {
    const open = menu.hidden;menu.hidden=!open;menuButton.setAttribute('aria-expanded',String(open));menuButton.setAttribute('aria-label',open?'Menyuni yopish':'Menyuni ochish');
  });
  menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>closeMenu()));
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!menu.hidden)closeMenu(true);});
  matchMedia('(min-width: 951px)').addEventListener('change',e=>{if(e.matches)closeMenu();});

  const dialog = document.getElementById('login-dialog');
  document.querySelectorAll('.login-trigger').forEach(button=>button.addEventListener('click',e=>{
    e.preventDefault();closeMenu();dialog.showModal();
  }));
  document.getElementById('close-login').addEventListener('click',()=>dialog.close());
  document.getElementById('dialog-partner').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{
    if(e.target!==dialog)return;const r=dialog.getBoundingClientRect();
    if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();
  });

  // Cabinet exploration uses accessible tabs, including keyboard navigation.
  const tabs=[...document.querySelectorAll('[data-product]')];
  const tabLabels={family:'OILAVIY KABINET',studio:'STUDIYA ISH MAYDONI',venue:'TO‘YXONA ISH MAYDONI'};
  function selectTab(tab,focus=false) {
    tabs.forEach(item=>{const active=item===tab;item.setAttribute('aria-selected',String(active));item.tabIndex=active?0:-1;document.getElementById(item.getAttribute('aria-controls')).hidden=!active;});
    document.getElementById('workbench-label').textContent=tabLabels[tab.dataset.product];
    if(focus)tab.focus();
  }
  tabs.forEach((tab,i)=>{
    tab.addEventListener('click',()=>selectTab(tab));
    tab.addEventListener('keydown',e=>{
      let next;if(e.key==='ArrowRight')next=(i+1)%tabs.length;if(e.key==='ArrowLeft')next=(i+tabs.length-1)%tabs.length;if(e.key==='Home')next=0;if(e.key==='End')next=tabs.length-1;
      if(next!==undefined){e.preventDefault();selectTab(tabs[next],true);}
    });
  });

  // Intentionally synthetic calendar: no booking is submitted from this illustration.
  const calendar=document.getElementById('calendar-days');
  for(let i=0;i<6;i++){const empty=document.createElement('span');empty.setAttribute('aria-hidden','true');calendar.append(empty);}
  const weekdays=['YAKSHANBA','DUSHANBA','SESHANBA','CHORSHANBA','PAYSHANBA','JUMA','SHANBA'];
  function selectDay(day) {
    calendar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.textContent)===day)));
    document.getElementById('selected-date').textContent=`${day}-NOYABR / ${weekdays[new Date(Date.UTC(2026,10,day)).getUTCDay()]}`;
    document.querySelectorAll('.session').forEach((session,i)=>{const available=(day+i)%3!==0;session.classList.toggle('available',available);session.classList.toggle('booked',!available);session.querySelector('b').textContent=available?'Bo‘sh':'Band';});
  }
  for(let day=1;day<=30;day++){
    const button=document.createElement('button');button.type='button';button.textContent=day;button.setAttribute('aria-label',`${day}-noyabr, namunaviy jadval`);button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>selectDay(day));calendar.append(button);
  }selectDay(14);

  // Demonstration only; all real permissions are enforced in the authenticated app.
  const people=['Buvijon','Onajon','Akam','Opam','Do‘stim'];
  const selected=new Set(), names={ '24H':'24 soat','3D':'3 kun','1W':'1 hafta','1M':'30 kun' };
  let duration='24H';
  const peopleBox=document.getElementById('share-people');
  people.forEach((name,i)=>{
    const button=document.createElement('button');button.type='button';button.className='person';button.innerHTML=`<span>+</span><small>${name}</small>`;button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',`${name}: namunaga qo‘shish`);
    button.addEventListener('click',()=>{selected.has(i)?selected.delete(i):selected.add(i);renderShare();});peopleBox.append(button);
  });
  function renderShare(){
    [...peopleBox.children].forEach((button,i)=>{const active=selected.has(i);button.setAttribute('aria-pressed',String(active));button.setAttribute('aria-label',`${people[i]}: ${active?'namunadan olib tashlash':'namunaga qo‘shish'}`);button.querySelector('span').textContent=active?people[i][0]:'+';});
    document.getElementById('share-count').textContent=`${selected.size} / 5`;
    const result=document.getElementById('share-result');result.replaceChildren();
    if(!selected.size){result.textContent='Yuqoridagi + belgilarini bosing. Bu namuna hech kimga haqiqiy taklif yubormaydi.';return;}
    const bold=document.createElement('strong');bold.textContent=[...selected].map(i=>people[i]).join(', ');
    result.append(bold,` taklifni qabul qilgach ${names[duration]} davomida ko‘ra oladi. Bu faqat namuna; haqiqiy taklif yuborilmadi.`);
  }
  document.querySelectorAll('[data-duration]').forEach(button=>button.addEventListener('click',()=>{duration=button.dataset.duration;document.querySelectorAll('[data-duration]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));renderShare();}));
  document.getElementById('reset-share').addEventListener('click',()=>{selected.clear();duration='24H';document.querySelectorAll('[data-duration]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.duration===duration)));renderShare();});

  document.querySelectorAll('[data-partner-kind]').forEach(link=>link.addEventListener('click',()=>{document.querySelector(`#apply-form [data-kind="${link.dataset.partnerKind}"]`).click();}));
  // Keep content readable when JavaScript or observation APIs are unavailable.
  if('IntersectionObserver' in window&&!reduced.matches){
    const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.remove('waiting');entry.target.classList.add('visible');observer.unobserve(entry.target);}}),{threshold:.07});
    document.querySelectorAll('[data-reveal]').forEach(element=>{element.classList.add('waiting');observer.observe(element);});
  }
  if('IntersectionObserver' in window){
    const sections=[...document.querySelectorAll('main section[id]')];
    const navObserver=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting)document.querySelectorAll('.desktop-nav a').forEach(a=>{const active=a.hash===`#${entry.target.id}`;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');});});},{rootMargin:'-15% 0px -60% 0px'});sections.forEach(s=>navObserver.observe(s));
  }
  const progress=document.getElementById('scroll-progress');let scheduled=false;
  function updateProgress(){const total=root.scrollHeight-innerHeight;progress.style.transform=`scaleX(${total>0?Math.min(1,Math.max(0,scrollY/total)):0})`;scheduled=false;}
  addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(updateProgress);}},{passive:true});addEventListener('resize',updateProgress);updateProgress();
})();
