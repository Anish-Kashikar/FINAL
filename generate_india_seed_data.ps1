# RAILSYNC India-wide synthetic demonstration data generator.
# This produces simulation-only data; it is not Indian Railways operational data.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$out = Join-Path $PSScriptRoot 'seed_data'
$preview = Join-Path $PSScriptRoot 'seed_preview'

$corridors = @(
  @('Andhra Pradesh: Vijayawada-Visakhapatnam','Vijayawada','Visakhapatnam',16.5062,80.6480,17.6868,83.2185,'Andhra Pradesh'), @('Arunachal Pradesh: Itanagar-Naharlagun','Itanagar','Naharlagun',27.0844,93.6053,27.1047,93.6952,'Arunachal Pradesh'),
  @('Assam: Guwahati-Dibrugarh','Guwahati','Dibrugarh',26.1445,91.7362,27.4728,94.9120,'Assam'), @('Bihar: Patna-Gaya','Patna','Gaya',25.5941,85.1376,24.7955,85.0079,'Bihar'),
  @('Chhattisgarh: Raipur-Bilaspur','Raipur','Bilaspur',21.2514,81.6296,22.0797,82.1409,'Chhattisgarh'), @('Goa: Madgaon-Vasco','Madgaon','Vasco',15.2832,73.9862,15.3989,73.8113,'Goa'),
  @('Gujarat: Ahmedabad-Vadodara','Ahmedabad','Vadodara',23.0225,72.5714,22.3072,73.1812,'Gujarat'), @('Haryana: Ambala-Faridabad','Ambala','Faridabad',30.3782,76.7767,28.4089,77.3178,'Haryana'),
  @('Himachal Pradesh: Shimla-Kalka','Shimla','Kalka',31.1048,77.1734,30.8398,76.9407,'Himachal Pradesh'), @('Jharkhand: Ranchi-Dhanbad','Ranchi','Dhanbad',23.3441,85.3096,23.7957,86.4304,'Jharkhand'),
  @('Karnataka: Bengaluru-Hubballi','Bengaluru','Hubballi',12.9716,77.5946,15.3647,75.124,'Karnataka'), @('Kerala: Ernakulam-Thiruvananthapuram','Ernakulam','Thiruvananthapuram',9.9816,76.2999,8.5241,76.9366,'Kerala'),
  @('Madhya Pradesh: Bhopal-Jabalpur','Bhopal','Jabalpur',23.2599,77.4126,23.1815,79.9864,'Madhya Pradesh'), @('Maharashtra: Mumbai-Nagpur','Mumbai','Nagpur',19.076,72.8777,21.1458,79.0882,'Maharashtra'),
  @('Manipur: Imphal-Jiribam','Imphal','Jiribam',24.817,93.9368,24.799,93.12,'Manipur'), @('Meghalaya: Shillong-Guwahati','Shillong','Guwahati',25.5788,91.8933,26.1445,91.7362,'Meghalaya'),
  @('Mizoram: Aizawl-Kolasib','Aizawl','Kolasib',23.7271,92.7176,24.2246,92.6764,'Mizoram'), @('Nagaland: Dimapur-Kohima','Dimapur','Kohima',25.904,93.727,25.6751,94.1086,'Nagaland'),
  @('Odisha: Bhubaneswar-Cuttack','Bhubaneswar','Cuttack',20.2961,85.8245,20.4625,85.883,'Odisha'), @('Punjab: Ludhiana-Amritsar','Ludhiana','Amritsar',30.901,75.8573,31.634,74.8723,'Punjab'),
  @('Rajasthan: Jaipur-Jodhpur','Jaipur','Jodhpur',26.9124,75.7873,26.2389,73.0243,'Rajasthan'), @('Sikkim: Gangtok-Rangpo','Gangtok','Rangpo',27.3389,88.6065,27.177,88.531,'Sikkim'),
  @('Tamil Nadu: Chennai-Madurai','Chennai','Madurai',13.0827,80.2707,9.9252,78.1198,'Tamil Nadu'), @('Telangana: Hyderabad-Warangal','Hyderabad','Warangal',17.385,78.4867,17.9689,79.5941,'Telangana'),
  @('Tripura: Agartala-Dharmanagar','Agartala','Dharmanagar',23.8315,91.2868,24.3667,92.1667,'Tripura'), @('Uttar Pradesh: Lucknow-Varanasi','Lucknow','Varanasi',26.8467,80.9462,25.3176,82.9739,'Uttar Pradesh'),
  @('Uttarakhand: Dehradun-Haridwar','Dehradun','Haridwar',30.3165,78.0322,29.9457,78.1642,'Uttarakhand'), @('West Bengal: Kolkata-Siliguri','Kolkata','Siliguri',22.5726,88.3639,26.7271,88.3953,'West Bengal')
)
$profiles = @(
  @('Engineering','Track','ENG-TRK'), @('Engineering','Turnout','ENG-TO'), @('Traction Distribution','OHE Mast','TD-OHE'),
  @('Traction Distribution','Traction Substation','TD-TSS'), @('Signal & Telecommunication','Signal','ST-SIG'), @('Signal & Telecommunication','Axle Counter','ST-AXC')
)
$locations=@(); $assets=@(); $tasks=@(); $blocks=@(); $trains=@(); $locN=0; $assetN=0; $taskN=0; $blockN=0; $trainN=0
$severity=@('Low','Medium','High','Critical'); $condition=@('Good','Fair','Poor','Critical'); $criticality=@('Medium','High','High','Critical'); $impact=@('Low','Medium','High'); $assetStatus=@('Operational','Operational','Under Observation','Maintenance In Progress'); $taskType=@('Inspection','Preventive Maintenance','Condition Monitoring','Corrective Maintenance')

foreach ($c in $corridors) {
  for ($i=0; $i -lt 6; $i++) {
    $locN++; $ratio=$i/5.0
    $loc=[pscustomobject]@{location_id=('LOC-{0:D3}' -f $locN);corridor=$c[0];state=$c[7];kilometer=[math]::Round(18+($i*42.5)+(($locN%3)*1.7),2);latitude=[math]::Round($c[3]+(($c[5]-$c[3])*$ratio),6);longitude=[math]::Round($c[4]+(($c[6]-$c[4])*$ratio),6)}
    $locations += $loc
    foreach ($p in $profiles) { $assetN++; $x=$assetN%4; $assets += [pscustomobject]@{asset_id=('AST-{0:D4}' -f $assetN);asset_code=('{0}-{1:D4}' -f $p[2],$assetN);asset_type=$p[1];department=$p[0];location_id=$loc.location_id;criticality=$criticality[$x];condition=$condition[($assetN+1)%4];last_maintenance=('2026-{0:D2}-{1:D2}' -f (3+($assetN%5)),(4+($assetN%24)));next_maintenance=('2026-{0:D2}-{1:D2}' -f (9+($assetN%3)),(3+($assetN%25)));status=$assetStatus[$x]} }
  }
  for ($b=0; $b -lt 4; $b++) { $blockN++; $hour=if($b -eq 0){5+(($blockN%2))}else{($blockN+$b)%3}; $start=Get-Date ('2026-09-{0:D2} {1:D2}:00:00' -f (2+$b*2),$hour); $duration=90+(($blockN%3)*30); $blocks += [pscustomobject]@{block_id=('BLK-{0:D3}' -f $blockN);corridor=$c[0];start_time=$start.ToString('yyyy-MM-dd HH:mm:ss');end_time=$start.AddMinutes($duration).ToString('yyyy-MM-dd HH:mm:ss');duration_minutes=$duration;capacity=(2+($blockN%3));status='Available'} }
  $serviceCount=6+(($blockN+$locN)%7)
  for ($t=0; $t -lt $serviceCount; $t++) { $trainN++; $offset=$t+$blockN; $start=Get-Date ('2026-09-{0:D2} {1:D2}:15:00' -f (1+($offset%6)),(3+(($offset*3+$blockN)%19))); $kind=if($offset%5 -eq 0){'Freight'}elseif($offset%4 -eq 0){'Express'}else{'Passenger'}; $trains += [pscustomobject]@{train_id=('TRN-{0:D3}' -f $trainN);train_number=(12000+$trainN);train_name=('{0} {1} Simulation Service' -f $c[1],$kind);corridor=$c[0];scheduled_start=$start.ToString('yyyy-MM-dd HH:mm:ss');scheduled_end=$start.AddMinutes(95+(($trainN%5)*30)).ToString('yyyy-MM-dd HH:mm:ss');priority=if($kind -eq 'Express'){'High'}else{'Normal'}} }
}
$backboneStates=@('Himachal Pradesh','Punjab','Haryana','Uttarakhand','Uttar Pradesh','Rajasthan','Gujarat','Maharashtra','Goa','Karnataka','Kerala','Tamil Nadu','Andhra Pradesh','Telangana','Madhya Pradesh','Chhattisgarh','Odisha','West Bengal','Jharkhand','Bihar','Sikkim','Assam','Arunachal Pradesh','Nagaland','Manipur','Mizoram','Tripura','Meghalaya')
foreach($state in $backboneStates){$origin=$locations|Where-Object {$_.state -eq $state}|Select-Object -First 1;if($origin){$locN++;$assetN++;$junction=[pscustomobject]@{location_id=('NET-{0:D3}' -f $locN);corridor='National Connectivity Backbone';state=$state;kilometer=$origin.kilometer;latitude=$origin.latitude;longitude=$origin.longitude};$locations+=$junction;$assets+=[pscustomobject]@{asset_id=('AST-{0:D4}' -f $assetN);asset_code=('NET-JNC-{0:D4}' -f $assetN);asset_type='Network Junction';department='Network Operations';location_id=$junction.location_id;criticality='Medium';condition='Good';last_maintenance='2026-06-01';next_maintenance='2026-12-01';status='Operational'}}
}
foreach ($asset in $assets) { if($asset.asset_type -eq 'Network Junction'){continue}; $loc=$locations | Where-Object location_id -eq $asset.location_id | Select-Object -First 1; for ($n=0; $n -lt 2; $n++) { $taskN++; $start=(Get-Date '2026-09-01 00:00:00').AddHours(($taskN*3)%504); $tasks += [pscustomobject]@{task_id=('TSK-{0:D4}' -f $taskN);asset_id=$asset.asset_id;location_id=$asset.location_id;corridor=$loc.corridor;task_type=$taskType[$taskN%4];description=('Synthetic demo: {0} at {1}' -f $asset.asset_type,$loc.location_id);severity=$severity[($taskN+$n)%4];failure_probability=[math]::Round(0.12+(($taskN%79)/100),2);asset_criticality=$asset.criticality;traffic_impact=$impact[$taskN%3];estimated_duration_minutes=(35+(($taskN*17)%71));required_department=$asset.department;earliest_start=$start.ToString('yyyy-MM-dd HH:mm:ss');deadline=$start.AddDays(2+($taskN%14)).ToString('yyyy-MM-dd HH:mm:ss');status=if($taskN%13 -eq 0){'In Progress'}elseif($taskN%17 -eq 0){'Scheduled'}else{'Pending'};priority_score=''} } }

$tables=@{'locations.csv'=$locations;'assets.csv'=$assets;'maintenance_tasks.csv'=$tasks;'railway_blocks.csv'=$blocks;'trains.csv'=$trains}
foreach($name in $tables.Keys){$tables[$name] | Export-Csv (Join-Path $out $name) -NoTypeInformation}
$sql=@('-- RAILSYNC India-wide synthetic demonstration dataset.','-- Simulation only: locations, services and maintenance records are illustrative and not operational Indian Railways data.','','BEGIN;')
foreach($r in $locations){$sql += "INSERT INTO locations (location_id, corridor, kilometer, latitude, longitude) VALUES ('$($r.location_id)', '$($r.corridor)', $($r.kilometer), $($r.latitude), $($r.longitude));"}
foreach($r in $assets){$sql += "INSERT INTO assets (asset_id, asset_code, asset_type, department, location_id, criticality, condition, last_maintenance, next_maintenance, status) VALUES ('$($r.asset_id)', '$($r.asset_code)', '$($r.asset_type)', '$($r.department)', '$($r.location_id)', '$($r.criticality)', '$($r.condition)', '$($r.last_maintenance)', '$($r.next_maintenance)', '$($r.status)');"}
foreach($r in $tasks){$sql += "INSERT INTO maintenance_tasks (task_id, asset_id, location_id, corridor, task_type, description, severity, failure_probability, asset_criticality, traffic_impact, estimated_duration_minutes, required_department, earliest_start, deadline, status, priority_score) VALUES ('$($r.task_id)', '$($r.asset_id)', '$($r.location_id)', '$($r.corridor)', '$($r.task_type)', '$($r.description)', '$($r.severity)', $($r.failure_probability), '$($r.asset_criticality)', '$($r.traffic_impact)', $($r.estimated_duration_minutes), '$($r.required_department)', '$($r.earliest_start)', '$($r.deadline)', '$($r.status)', NULL);"}
foreach($r in $blocks){$sql += "INSERT INTO railway_blocks (block_id, corridor, start_time, end_time, duration_minutes, capacity, status) VALUES ('$($r.block_id)', '$($r.corridor)', '$($r.start_time)', '$($r.end_time)', $($r.duration_minutes), $($r.capacity), '$($r.status)');"}
foreach($r in $trains){$sql += "INSERT INTO trains (train_id, train_number, train_name, corridor, scheduled_start, scheduled_end, priority) VALUES ('$($r.train_id)', '$($r.train_number)', '$($r.train_name)', '$($r.corridor)', '$($r.scheduled_start)', '$($r.scheduled_end)', '$($r.priority)');"}
$sql += 'COMMIT;'; [System.IO.File]::WriteAllLines((Join-Path $out 'seed.sql'),$sql,[System.Text.UTF8Encoding]::new($false))
foreach($name in @('locations.csv','assets.csv','maintenance_tasks.csv','railway_blocks.csv','trains.csv','seed.sql')){Copy-Item (Join-Path $out $name) (Join-Path $preview $name) -Force}
Write-Output "Generated $($locations.Count) locations, $($assets.Count) assets, $($tasks.Count) tasks, $($blocks.Count) blocks and $($trains.Count) train services."
