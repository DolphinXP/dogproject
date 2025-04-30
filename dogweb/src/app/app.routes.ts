import {Routes} from '@angular/router';
import {JustTestComponent} from '../just-test/just-test.component';
import {MainComponent} from '../main/main.component';

export const routes: Routes = [
  {path: 'test', component: JustTestComponent},
  {path: '**', component: MainComponent},
];
