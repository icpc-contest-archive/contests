# Empty website crawls — ruling table 2026-10-21

95 contests whose only website crawl found nothing (Wayback CDX empty). Columns: the catalogue web locator, its live health, and sibling editions of the same series on the same host that DID crawl. A complete sibling pattern on a healthy host means the URL most likely never existed -> `web: null` + note (as done for gny-1995). A dead host with no crawled siblings proves nothing -> keep the locator; it may be Wayback-excluded.

| contest | web | live | evidence | siblings on host | which |
|---|---|---|---|---|---|
| algeria-2024 | https://acpc.global/event/alcpc2024/ | dead | HTTP 404 | 0 |  |
| amritapuri-2019 | http://xxx.yyy.edu | dead | URLError: SOCKS5 connect to xxx.yyy.edu: | 0 |  |
| chennai-2023 | https://codedrills.io/contests/icpc-chennai-2023-regional-round | dead | URLError: SOCKS5 connect to codedrills.i | 0 |  |
| colombia-maraton-2013 | https://www.utadeo.edu.co/es/noticia/concursos/ingenieria-de-sistemas/83/maraton-nacional-de-programacion-acis-redis-2013 | dead | HTTP 403 | 0 |  |
| colombia-maraton-2015 | http://www.afacom.org/secciones/ultimas-noticias/1975-xxix-maraton-nacional-de-programacion-2015-en-el-politecnico-grancolombiano | dead | URLError: timed out | 0 |  |
| colombia-maraton-2016 | https://www.notingenio.com.co/noticias-tecnologia/los-equipos-de-la-universidad-nacional-de-bogota-ganaron-la-xxx-maraton-nacional-de-programacion-de-colombia-acis-redis-2016/ | dead | URLError: SOCKS5 connect to www.notingen | 0 |  |
| dalian-2016 | http://2016acm.dlmu.edu.cn/ | dead | URLError: SOCKS5 connect to 2016acm.dlmu | 0 |  |
| dhaka-2007 | http://icpc.bubt.edu.bd/2007 | changed | HTTP 200; never mentions year 2007±1 | 12 | dhaka-1997, dhaka-1998, dhaka-1999, dhaka-2013, dhaka-2014, dhaka-2015 |
| dhaka-2010 | http://icpc.bubt.edu.bd/2010 | changed | HTTP 200; never mentions year 2010±1 | 12 | dhaka-1997, dhaka-1998, dhaka-1999, dhaka-2013, dhaka-2014, dhaka-2015 |
| dhaka-2011 | http://icpc.bubt.edu.bd/2011 | changed | HTTP 200; never mentions year 2011±1 | 12 | dhaka-1997, dhaka-1998, dhaka-1999, dhaka-2013, dhaka-2014, dhaka-2015 |
| erc-1991 | https://dl.acm.org/doi/10.1145/170791.171152 | dead | HTTP 403 | 0 |  |
| ethiopia-2018 | https://contest.icpcethiopia.org | dead | URLError: SOCKS5 connect to contest.icpc | 0 |  |
| gny-1995 | http://acmgnyr.org/year1995/ | dead | HTTP 404 | 29 | gny-1997, gny-1998, gny-1999, gny-2000, gny-2001, gny-2002, gny-2003,  |
| gny-1996 | http://acmgnyr.org/year1996/ | dead | HTTP 404 | 29 | gny-1997, gny-1998, gny-1999, gny-2000, gny-2001, gny-2002, gny-2003,  |
| hungary-2023 | https://cs.bme.hu/icpc/posts/2023-10-14-icpc-hungary-results/ | dead | URLError: [SSL: CERTIFICATE_VERIFY_FAILE | 2 | hungary-2007, hungary-2008 |
| kabul-2025 | http://icpc.kateb.edu.af/blogs/ICPC_2025%E2%80%932026_Kabul_Regional_Programming_Contest_Report | dead | HTTP 500 | 3 | kabul-2018, kabul-2019, kabul-2020 |
| kuwait-2014 | https://kcpc2018.wordpress.com/history/ | live | HTTP 200; mentions year 2014±1 | 2 | kuwait-2017, kuwait-2018 |
| kuwait-2015 | http://www.aou.edu.kw/KCPC2015/ | dead | URLError: timed out | 0 |  |
| kuwait-2016 | https://kcpc2018.wordpress.com/history/ | live | HTTP 200; mentions year 2014±1 | 2 | kuwait-2017, kuwait-2018 |
| mausa-1997 | https://www.cs.drexel.edu/~popyack/ACM/contest.1997.html | dead | URLError: [SSL: CERTIFICATE_VERIFY_FAILE | 0 |  |
| mausa-2013 | http://acm-midatl.radford.edu:8080 | dead | URLError: SOCKS5 connect to acm-midatl.r | 0 |  |
| mcpc-1993 | https://catsofwywop.com/icpc/data/mcpc/2000/browse.html | dead | URLError: [SSL: CERTIFICATE_VERIFY_FAILE | 0 |  |
| mcpc-1994 | https://catsofwywop.com/icpc/data/mcpc/2000/browse.html | dead | URLError: [SSL: CERTIFICATE_VERIFY_FAILE | 0 |  |
| nanchang-2019 | https://icpc.jxnu.edu.cn | dead | URLError: SOCKS5 connect to icpc.jxnu.ed | 0 |  |
| nanjing-2019 | http://xxx.yyy.edu | dead | URLError: SOCKS5 connect to xxx.yyy.edu: | 0 |  |
| nena-atlantic-2008 | http://www.umoncton.ca/apics-cipas08/html/competitions.html | dead | HTTP 404 | 0 |  |
| nena-atlantic-2013 | http://conferences.upei.ca/samscs2013/competitions/ | dead | URLError: timed out | 0 |  |
| nena-east-2008 | https://hc3.seas.harvard.edu/hc3/bospre/2008 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| nena-east-2009 | https://hc3.seas.harvard.edu/hc3/bospre/2009 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| nena-east-2010 | https://hc3.seas.harvard.edu/hc3/bospre/2010 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| nena-east-2011 | https://hc3.seas.harvard.edu/hc3/bospre/2011 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| nena-east-2012 | https://hc3.seas.harvard.edu/hc3/bospre/2012 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| nena-east-2013 | https://hc3.seas.harvard.edu/hc3/bospre/2013 | dead | URLError: SOCKS5 connect to hc3.seas.har | 4 | nena-east-2015, nena-east-2017, nena-east-2018, nena-east-2019 |
| poland-2015 | http://www.amppz.ii.uni.wroc.pl/2015 | changed | never mentions year 2015±1 (no snapshot  | 1 | poland-2017 |
| poland-2016 | http://www.amppz.ii.uni.wroc.pl/2016/ | changed | never mentions year 2016±1 (no snapshot  | 1 | poland-2017 |
| poland-2018 | http://www.amppz.ii.uni.wroc.pl/2018 | changed | never mentions year 2018±1 (no snapshot  | 1 | poland-2017 |
| rmc-1998 | http://clem.mscd.edu/~howerton/ACM/RM98Home.html | dead | URLError: SOCKS5 connect to clem.mscd.ed | 0 |  |
| seerc-1995 | https://seerc.icpc.global/1995/ | dead | HTTP 403 | 0 |  |
| seerc-1996 | https://seerc.icpc.global/1996/ | dead | HTTP 403 | 0 |  |
| seerc-1997 | https://seerc.icpc.global/1997/ | dead | HTTP 403 | 0 |  |
| seerc-1998 | https://seerc.icpc.global/1998/ | dead | HTTP 403 | 0 |  |
| seerc-1999 | https://seerc.icpc.global/1999/ | dead | HTTP 403 | 0 |  |
| seerc-2000 | https://seerc.icpc.global/2000/ | dead | HTTP 403 | 0 |  |
| seerc-2001 | https://seerc.icpc.global/2001/ | dead | HTTP 403 | 0 |  |
| seerc-2002 | https://seerc.icpc.global/2002/ | dead | HTTP 403 | 0 |  |
| seerc-2003 | https://seerc.icpc.global/2003/ | dead | HTTP 403 | 0 |  |
| seerc-2004 | https://seerc.icpc.global/2004/ | dead | HTTP 403 | 0 |  |
| seerc-2005 | https://seerc.icpc.global/2005/ | dead | HTTP 403 | 0 |  |
| seerc-2006 | https://seerc.icpc.global/2006/ | dead | HTTP 403 | 0 |  |
| seerc-2007 | https://seerc.icpc.global/2007/ | dead | HTTP 403 | 0 |  |
| seerc-2008 | https://seerc.icpc.global/2008/ | dead | HTTP 403 | 0 |  |
| seerc-2009 | https://seerc.icpc.global/2009/ | dead | HTTP 403 | 0 |  |
| seerc-2010 | https://seerc.icpc.global/2010/ | dead | HTTP 403 | 0 |  |
| seerc-2011 | https://seerc.icpc.global/2011/ | dead | HTTP 403 | 0 |  |
| seerc-2012 | https://seerc.icpc.global/2012/ | dead | HTTP 403 | 0 |  |
| seerc-2013 | https://seerc.icpc.global/2013/ | dead | HTTP 403 | 0 |  |
| seerc-2014 | https://seerc.icpc.global/2014/ | dead | HTTP 403 | 0 |  |
| seerc-2015 | https://seerc.icpc.global/2015/ | dead | HTTP 403 | 0 |  |
| seerc-2016 | https://seerc.icpc.global/2016/ | dead | HTTP 403 | 0 |  |
| seerc-2017 | https://seerc.icpc.global/2017/ | dead | HTTP 403 | 0 |  |
| seerc-2018 | https://seerc.icpc.global/2018/ | dead | HTTP 403 | 0 |  |
| seerc-2019 | https://seerc.icpc.global/2019/ | dead | HTTP 403 | 0 |  |
| seerc-2020 | https://seerc.icpc.global/2020/ | dead | HTTP 403 | 0 |  |
| seerc-2021 | https://seerc.icpc.global/2021/ | dead | HTTP 403 | 0 |  |
| seerc-2022 | https://seerc.icpc.global/2022/ | dead | HTTP 403 | 0 |  |
| seerc-2023 | https://seerc.icpc.global/2023/ | dead | HTTP 403 | 0 |  |
| seerc-2024 | https://seerc.icpc.global/2024/ | changed | never mentions year 2024±1 (no snapshot  | 0 |  |
| seusa-1999 | http://icpc.baylor.edu/icpc/regionals/seusa99/home.shtml | dead | HTTP 403 | 0 |  |
| shenyang-2019 | http://xxx.yyy.edu | dead | URLError: SOCKS5 connect to xxx.yyy.edu: | 0 |  |
| slovenia-2009 | http://upm.fri.uni-lj.si/ | dead | URLError: SOCKS5 connect to upm.fri.uni- | 0 |  |
| slovenia-2010 | http://upm.fri.uni-lj.si/ | dead | URLError: SOCKS5 connect to upm.fri.uni- | 0 |  |
| socal-1979 | http://www.socalcontest.org/history/1979/results-1979.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1980 | http://www.socalcontest.org/history/1980/results-1980.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1981 | http://www.socalcontest.org/history/1981/results-1981.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1982 | http://www.socalcontest.org/history/1982/results-1982.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1983 | http://www.socalcontest.org/history/1983/results-1983.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1984 | http://www.socalcontest.org/history/1984/results-1984.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1985 | http://www.socalcontest.org/history/1985/results-1985.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1986 | http://www.socalcontest.org/history/1986/results-1986.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1987 | http://www.socalcontest.org/history/1987/results-1987.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1988 | http://www.socalcontest.org/history/1988/results-1988.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1990 | http://www.socalcontest.org/history/1990/results-1990.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1991 | http://www.socalcontest.org/history/1991/results-1991.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| socal-1993 | http://www.socalcontest.org/history/1993/results-1993.shtml | dead | HTTP 404 | 32 | socal-1989, socal-1995, socal-1996, socal-1997, socal-1998, socal-1999 |
| south-pacific-2018 | https://acmicpc.unisa.edu.au/index.php/regional-contest-current/8-regional-contests/162-2018-south-pacific-region-contests | dead | URLError: SOCKS5 connect to acmicpc.unis | 2 | south-pacific-2016, south-pacific-2017 |
| taiwan-ncpc-2007 | https://ncpc.ntnu.edu.tw/ncpc2007/ | dead | HTTP 404 | 1 | taiwan-ncpc-2014 |
| taiwan-ncpc-2013 | https://ncpc.ntnu.edu.tw/ncpc2013/ | dead | HTTP 404 | 1 | taiwan-ncpc-2014 |
| tap-2014 | http://www.torneoprogramacion.com.ar/2014 | dead | HTTP 404 | 0 |  |
| thailand-2017 | http://www.ict.mahidol.ac.th/acmicpc2017/ | dead | HTTP 404 | 1 | thailand-2018 |
| thailand-national-2013 | https://www.eng.psu.ac.th/old-website/8-information/365-5-acm-icpc-thailand-2013 | dead | HTTP 404 | 0 |  |
| torneo-chileno-2017 | http://www.inf.unap.cl/index.php/2017/08/28/icci-participa-en-el-torneo-chileno-de-programacion/ | dead | HTTP 403 | 0 |  |
| turkey-2010 | https://icpc.baylor.edu/regionals/finder/Turkey-2011 | dead | URLError: [SSL: SSLV3_ALERT_HANDSHAKE_FA | 5 | turkey-2011, turkey-2012, turkey-2013, turkey-2014, turkey-2018 |
| ukraine-2015 | http://icpc.baylor.edu/private/contest/AUCPC-2015?cid=1 | dead | HTTP 403 | 0 |  |
| xian-2002 | http://acm.xjtu.edu.cn/ | dead | URLError: timed out | 0 |  |
| yinchuan-2019 | http://xxx.yyy.edu | dead | URLError: SOCKS5 connect to xxx.yyy.edu: | 0 |  |

Empty crawl dirs for ids not in the catalogue (stale, deletable): `turkey/turkey-2015/website/2026-09-07-wayback-c4c06148`, `turkey/turkey-2016/website/2026-09-07-wayback-faa1e265`, `turkey/turkey-2017/website/2026-09-07-wayback-8574fbbb`
